"""Banka Creditas a.s.

Todo:
    This module is a work in progress. It needs a major rework.

docs:
    https://www.creditas.cz/firma/creditas-api/
"""

import base64
from datetime import date
from decimal import Decimal

import creditas
from beancount.core.data import Amount, Transaction
from beancount.core.flags import FLAG_WARNING
from lxml import etree

from ..bean_helpers import create_posting, create_transaction
from . import prepare_meta


def _get_transactions(token: str, account_id: str, from_date: date) -> bytes:
    # Creditas API v 1.0.0:
    # Manually generated token can be used only with the following URLs (and
    # the corresponding methods):
    #   /account/current/get
    #   /account/savings/get
    #   /account/balance/get
    #   /account/transaction/search
    #   /account/transaction/export
    #   /account/statement/list
    #   /account/statement/get

    config = creditas.Configuration()
    config.access_token = token
    api = creditas.TransactionApi(creditas.ApiClient(config))
    body = creditas.Body8(
        account_id=account_id,
        format="XML",
        filter=creditas.AccountTransactionFilter(date_from=from_date),
    )
    # TODO: handle creditas.rest.ApiException
    data: creditas.InlineResponse20011 = api.d_ps_account_transaction_export_api(
        body=body,
    )
    # TODO: handle other exceptions
    return base64.b64decode(data.export)


# FIXME: This function has to be turned into a class implementing ApiImporterProtocol.
def get_transactions(  # noqa: D103
    token: str,
    account_id: str,
    bean_account: str,
    from_date: date,
) -> tuple[list[Transaction], Amount]:
    # TODO: handle etree.XMLSyntaxError
    # TODO: handle other exceptions
    xml_root = etree.fromstring(  # noqa: S320
        _get_transactions(token, account_id, from_date),
    )
    nsmap = xml_root.nsmap

    # TODO: handle other exceptions
    # TODO: raise if not found
    def get_amount(element) -> Amount:
        amount = element.find("./Amt", nsmap)
        number = Decimal(amount.text)
        currency = amount.attrib["Ccy"]
        if element.find("./CdtDbtInd", nsmap).text == "DBIT":
            number = -number
        return Amount(number, currency)

    # TODO: handle other exceptions
    def get_text(element, xpath: str, *, raise_if_none: bool = False) -> str | None:
        text: str | None = element.findtext(xpath, default=None, namespaces=nsmap)
        if raise_if_none and text is None:
            # TODO: raise a custom exception
            raise
        return text

    statement = xml_root.find("./BkToCstmrStmt/Stmt", nsmap)
    balance = get_amount(statement.find("./Bal", nsmap))
    num_entries = get_text(
        statement,
        "./TxsSummry/TtlNtries/NbOfNtries",
        raise_if_none=True,
    )
    if num_entries == 0:
        return ([], balance)
    txns: list[Transaction] = []
    for entry in statement.findall("./Ntry", nsmap):
        if get_text(entry, "./CdtDbtInd", raise_if_none=True) == "DBIT":
            # Whether the related party is a debitor or a creditor.
            ind = "Cdtr"
        else:
            ind = "Dbtr"
        details = "./NtryDtls/TxDtls"
        # TODO: change `transaction_id` to `id` and `recipient_message`
        #   to `remittance_info`
        meta = prepare_meta(
            {
                "transaction_id": get_text(entry, "./NtryRef", raise_if_none=True),
                "account_id": get_text(
                    entry,
                    f"{details}/RltdPties/{ind}Acct/Id/Othr/Id",
                ),
                "bank_id": get_text(
                    entry,
                    f"{details}/RltdAgts/{ind}Agt/FinInstnId/Othr/Id",
                ),
                "ks": get_text(entry, f"{details}/Refs/InstrId"),
                "vs": get_text(entry, f"{details}/Refs/EndToEndId"),
                "ss": get_text(entry, f"{details}/Refs/PmtInfId"),
                "recipient_message": get_text(entry, f"{details}/RmtInf/Ustrd"),
                "executor": get_text(entry, f"{details}/RltdPties/{ind}/Nm"),
            },
        )
        txns.append(
            create_transaction(
                _date=date.fromisoformat(
                    get_text(
                        entry,
                        "./BookgDt/Dt",
                        raise_if_none=True,
                    ),  # type: ignore[arg-type]
                ),
                flag=FLAG_WARNING,
                postings=[
                    create_posting(
                        account=bean_account,
                        units=get_amount(entry),
                    ),
                ],
                meta=meta,
            ),
        )
    return (txns, balance)
