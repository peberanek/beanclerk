"""API Importer Protocol and utilities for custom importers."""

import abc
from datetime import date
from decimal import Decimal
from typing import Any

import beancount.core.data as bean_data
import lxml.etree

# from ..bean_helpers import create_posting, create_transaction
# from ..exceptions import ImporterError
from .. import bean_helpers, exceptions

TransactionReport = tuple[list[bean_data.Transaction], bean_data.Amount]


def refine_meta(meta: dict[str, Any]) -> dict[str, str]:
    """Return a dict of refined metadata for a Beancount transaction.

    Refinements:
        * removes empty strings
        * removes None values
        * converts all values to strings

    Args:
        meta (dict[str, Any]): a dict of transaction metadata

    Returns:
        dict[str, str]: a new dict of transaction metadata
    """
    new_meta = {}
    for k, v in meta.items():
        if not (v is None or v == ""):
            new_meta[k] = str(v)
    return new_meta


def parse_camt_053_001_02(xml: bytes, bean_account: str) -> TransactionReport:
    """Return a tuple with a list of Beancount transactions and the current balance.

    Args:
        xml (bytes): XML data (camt.053.001.02) as bytes
            https://cbaonline.cz/formaty-xml-pro-vzajemnou-komunikaci-bank-s-klienty
        bean_account (str): a Beancount account name

    Returns:
        TransactionReport: A tuple with the list of transactions and
            the current balance.
    """
    try:
        xml_root = lxml.etree.fromstring(xml)  # noqa: S320
    except lxml.etree.XMLSyntaxError as exc:
        raise exceptions.ImporterError(f"Invalid XML data: {exc}") from exc
    nsmap = xml_root.nsmap

    def get_amount(element) -> bean_data.Amount:
        amount = element.find("./Amt", nsmap)
        if amount is None:
            raise exceptions.ImporterError(
                f"Missing amount in the XML element '{element}'"
            )
        number = Decimal(amount.text)
        currency = amount.attrib["Ccy"]
        if element.find("./CdtDbtInd", nsmap).text == "DBIT":
            number = -number
        return bean_data.Amount(number, currency)

    def get_text(element, xpath: str, *, raise_if_none: bool = False) -> str | None:
        text: str | None = element.findtext(xpath, default=None, namespaces=nsmap)
        if raise_if_none and text is None:
            raise exceptions.ImporterError(
                f"Missing text in the XML element '{element}'"
            )
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
    txns: list[bean_data.Transaction] = []
    for entry in statement.findall("./Ntry", nsmap):
        # Related party may be a debitor or a creditor.
        if get_text(entry, "./CdtDbtInd", raise_if_none=True) == "DBIT":
            ind = "Cdtr"
        else:
            ind = "Dbtr"
        details = "./NtryDtls/TxDtls"
        meta = refine_meta(
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
            bean_helpers.create_transaction(
                _date=date.fromisoformat(
                    get_text(
                        entry,
                        "./BookgDt/Dt",
                        raise_if_none=True,
                    ),  # type: ignore[arg-type]
                ),
                postings=[
                    bean_helpers.create_posting(
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

    All API importers must comply with this interface.

    Abstract methods:
        fetch_transactions: fetch transactions from the API

    Each transaction should have `id` key in its metadata representing a unique
    transaction ID (for the given account). Beanclerk relies on this key when
    checking for duplicates and determining the date of the last imported
    transaction.
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

        Raises:
            beanclerk.exceptions.ImporterError: when the API returns an error or
                the data are for some reason invalid.

        Returns:
            TransactionReport: A tuple with the list of transactions and
                the current balance.
        """
