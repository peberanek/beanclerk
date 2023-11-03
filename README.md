# Beanclerk

[![version on pypi](https://img.shields.io/pypi/v/beanclerk)](https://pypi.org/project/beanclerk/)
[![license](https://img.shields.io/pypi/l/beanclerk)](https://pypi.org/project/beanclerk/)
[![python versions](https://img.shields.io/pypi/pyversions/beanclerk)](https://pypi.org/project/beanclerk/)
[![ci tests](https://github.com/peberanek/beanclerk/actions/workflows/tests.yml/badge.svg)](https://github.com/peberanek/beanclerk/actions/workflows/tests.yml)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/peberanek/beanclerk/main.svg)](https://results.pre-commit.ci/latest/github/peberanek/beanclerk/main)

Beanclerk is an extension for [Beancount](https://github.com/beancount/beancount) (Double-Entry Accounting from Text Files). It automates some areas not addressed by Beancount itself, specifically:

1. Network downloads (via APIs)
1. Categorization
1. Insertion of new transactions

(For rationale see [Notes](#notes).)

Supported data sources:

* [Fio banka](https://www.fio.cz/),
* [Banka Creditas](https://www.creditas.cz/),
* or any other source implementing the [API Importer Protocol](https://github.com/peberanek/beanclerk/blob/main/beanclerk/importers/__init__.py).

## Example

Beanclerk requires a [config file](https://github.com/peberanek/beanclerk/blob/main/tests/beanclerk-config.yml), typically saved alongside an existing ledger:
```
$ ls
beanclerk-config.yml  my_ledger.beancount
```

With a valid config, import new transactions via the `import` command:
```
$ bean-clerk import
Account: 'Assets:Banks:Fio:Checking'
  New transactions: 3, balance OK: 9830.00 CZK
Account: 'Assets:Banks:Fio:Savings'
  New transactions: 0, balance OK: 50001.97 CZK
```

> [!IMPORTANT]
> Beanclerk relies on presence of `id` key in transaction metadata to (1) check for duplicates and (2) to determine the date of the last import. So, you may set the initial import date by adding a transaction like this:
> ```
> 2023-01-01 * "Initial import date for Beanclerk"
>   id: "dummy"
>   Assets:Banks:Fio:Checking   0 CZK
>   Assets:Banks:Fio:Savings    0 CZK
> ```
> Make sure to include all accounts defined in the config file.

Once Beanclerk encounters a transaction without a matching categorization rule, it fires up an interactive prompt:
```
$ bean-clerk import
Account: 'Assets:Banks:Fio:Checking'
...
No categorization rule matches the following transaction:
Transaction(
    meta={
        'id': '10000000002',
        'account_id': '2345678901',
        'account_name': 'Pavel, Žák',
        'bank_id': '2010',
        'bank_name': 'Fio banka, a.s.',
        'type': 'Příjem převodem uvnitř banky',
        'specification': 'test specification',
        'bic': 'TESTBICXXXX',
        'order_id': '30000000002',
        'payer_reference': 'test payer reference'
    },
    date=datetime.date(2023, 1, 3),
    flag='*',
    payee=None,
    narration='',
    tags=frozenset(),
    links=frozenset(),
    postings=[
        Posting(
            account='Assets:Banks:Fio:Checking',
            units=500.0 CZK,
            cost=None,
            price=None,
            flag=None,
            meta={}
        )
    ]
)
Available actions:
'r': reload config (you should add a new rule first)
'i': import as-is (transaction remains unbalanced)
...
```

## Installation

```
pip install beanclerk
```

> [!IMPORTANT]
> Beanclerk requires Beancount (v2). As some of its core modules are written in C/C++, you may need `gcc` and `python3-devel` (`python3-dev` on some distros) for its successful installation. For further details check out [Beancount Download & Installation](https://docs.google.com/document/d/1FqyrTPwiHVLyncWTf3v5TcooCu9z5JRX8Nm41lVZi0U/edit#heading=h.rs27hvxo0wyl).

If you prefer to install Beanclerk in an isolated environment, instead of pip use [pipx](https://github.com/pypa/pipx):
```
pipx install beanclerk
```

Confirm successful installation by running:
```
bean-clerk -h
```

## Notes

**Beanclerk is still a rather 'rough' prototype.** You may encounter some unhandled exceptions and the API may change significantly in the future. It is tested on Linux only.

As mentioned above, Beanclerk automates some areas not addressed by Beancount:

1. [_Network downloads_](https://beancount.github.io/docs/importing_external_data.html#automating-network-downloads): As financial institutions start to provide access to their services via APIs, it is more convenient and less error-prone to use them instead of a manual download and multi-step import from CSV (or similar) reports. Compared to these reports, APIs usually have a stable specification and provide transaction IDs, making the importing process (e.g. checking for duplicates) much easier. Therefore, inspired by Beancount [Importer Protocol](https://beancount.github.io/docs/importing_external_data.html#writing-an-importer), Beanclerk proposes a simple [API Importer Protocol](https://github.com/peberanek/beanclerk/blob/main/beanclerk/importers/__init__.py) to support any compatible API.
1. [_Automated categorization_](https://beancount.github.io/docs/importing_external_data.html#automatic-categorization): With growing number of new transactions, manual categorization quickly becomes repetitive, boring and therefore error-prone. So, why not to leave the hard part for machines and then just tweak the details?
    * As the first step, Beanclerk provides a way to define rules for automated categorization.
    * The future step is to augment it by machine-learning capabilities (e.g. via integration of the [Smart Importer](https://github.com/beancount/smart_importer)). (Btw, it might be also interesting to use machine-learning to discover patterns or to provide predictions about our financial behavior.)
1. _Automatic insertion of new transactions_: Beanclerk _appends_ transactions to the Beancount input file (i.e. the ledger) defined in the configuration. It saves the step of doing this manually. (I don't care about a precise position of new transactions in the ledger because reporting tools like [Fava](https://github.com/beancount/fava) sort and filter them effectively.) Consider to keep your ledger under a version control (e.g. via Git) to make any changes easy to review.

### Similar projects

I started Beanclerk primarily to try out some Python packages and to get better in programming by automating my daily workflow. Actually, there are a couple of interesting projects of similar sort, which may provide inspiration or alternative solutions to the areas described above:

* [beancount-import](https://github.com/jbms/beancount-import): Web UI for semi-automatically importing external data into beancount.
* [finance-dl](https://github.com/jbms/finance-dl): Tools for automatically downloading/scraping personal financial data.
* [beancount_reds_importers](https://github.com/redstreet/beancount_reds_importers): Simple ingesting tools for Beancount (plain text, double entry accounting software). More importantly, a framework to allow you to easily write your own importers.
* [smart_importer](https://github.com/beancount/smart_importer): Augment Beancount importers with machine learning functionality.
* [autobean](https://github.com/SEIAROTg/autobean): A collection of plugins and scripts that help automating bookkeeping with beancount.

## Contributing

Contributions are welcome. As changes the project is still changing rapidly, make sure to create an issue first so we can discuss it.

Set up a development environment:
```bash
pipenv install --dev -e .
pipenv run pre-commit install
```

> [!NOTE]
> If you prefer to create the virtual environment in the project's directory, add `PIPENV_VENV_IN_PROJECT=1` into `.env` file. For more info see [Virtualenv mapping caveat](https://pipenv.pypa.io/en/latest/installation/#virtualenv-mapping-caveat).

Run tests:
```bash
pytest
```

Follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/).

## License

Following the Beancount license, this code is distributed under the terms of the "GNU GPLv2 only". See `LICENSE` file for details.
