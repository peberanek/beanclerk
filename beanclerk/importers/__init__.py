"""API Importer Protocol and utilities for custom importers."""

import abc
from datetime import date
from decimal import Decimal
from typing import Any

from beancount.core.data import Amount, Transaction
from beancount.core.flags import FLAG_WARNING
from lxml import etree

from ..bean_helpers import create_posting, create_transaction

TransactionReport = tuple[list[Transaction], Amount]


def prepare_meta(d: dict[str, Any]) -> dict[str, str]:
    """Return a dict of metadata for a Beancount transaction.

    Args:
        d (dict[str, Any]): a dict of values

    Returns:
        dict[str, str]: a dict of metadata
    """
    meta = {}
    for k, v in d.items():
        if not (v is None or v == ""):
            meta[k] = str(v)
    return meta


def parse_camt_053_001_02(xml: bytes, bean_account: str) -> TransactionReport:
    """Return a tuple with a list of Beancount transactions and the current balance.

    Args:
        xml (bytes): bytes with the XML data (camt.053.001.02)
            https://cbaonline.cz/formaty-xml-pro-vzajemnou-komunikaci-bank-s-klienty
        bean_account (str): a Beancount account name

    Returns:
        TransactionReport: A tuple with the list of transactions and
            the current balance.
    """
    # TODO: handle etree.XMLSyntaxError
    # TODO: handle other exceptions
    xml_root = etree.fromstring(xml)  # noqa: S320
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
        # Related party may be a debitor or a creditor.
        if get_text(entry, "./CdtDbtInd", raise_if_none=True) == "DBIT":
            ind = "Cdtr"
        else:
            ind = "Dbtr"
        details = "./NtryDtls/TxDtls"
        meta = prepare_meta(
            {
                "id": get_text(entry, "./NtryRef", raise_if_none=True),
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
                "remittance_info": get_text(entry, f"{details}/RmtInf/Ustrd"),
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
        txns.sort(key=lambda txn: txn.date)
    return (txns, balance)


class ApiImporterProtocol(abc.ABC):
    """API Importer Protocol for custom importers.

    All API importers must comply with this interface. Make sure to implement
    all methods decorated with `@abc.abstractmethod`. There are no restrictions
    on other methods, variables or properties.
    """

    @abc.abstractmethod
    def fetch_transactions(
        self,
        bean_account: str,
        from_date: date,
        to_date: date,
    ) -> TransactionReport:
        """Return a tuple with a list of Beancount transactions and the current balance.

        Args:
            bean_account (str): a Beancount account name
            from_date (date): the first date to import
            to_date (date): the last date to import

        Returns:
            TransactionReport: A tuple with the list of transactions and
                the current balance.
        """
