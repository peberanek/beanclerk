# Beanclerk

[![version on pypi](https://img.shields.io/pypi/v/beanclerk)](https://pypi.org/project/beanclerk/)
[![license](https://img.shields.io/pypi/l/beanclerk)](https://pypi.org/project/beanclerk/)
[![python versions](https://img.shields.io/pypi/pyversions/beanclerk)](https://pypi.org/project/beanclerk/)
[![ci tests](https://github.com/peberanek/beanclerk/actions/workflows/tests.yml/badge.svg)](https://github.com/peberanek/beanclerk/actions/workflows/tests.yml)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/peberanek/beanclerk/main.svg)](https://results.pre-commit.ci/latest/github/peberanek/beanclerk/main)

## Description

Beanclerk is an extension for [Beancount](https://github.com/beancount/beancount) (a useful tool for managing personal finance), automating some areas not addressed by Beancount itself, namely:

1. [_Network downloads_](https://beancount.github.io/docs/importing_external_data.html#automating-network-downloads): As some financial institutions start to provide access to their services via APIs, it is more convenient and less error-prone to use them instead of a manual download and multi-step import process from CSV (or similar) reports. Compared to these reports, APIs usually have a stable specification and provide transaction IDs, making the importing process (e.g. checking for duplicates) much easier. Therefore, inspired by Beancount [Importer Protocol](https://beancount.github.io/docs/importing_external_data.html#writing-an-importer), Beanclerk proposes a simple [API Importer Protocol](https://github.com/peberanek/beanclerk/blob/main/beanclerk/importers/__init__.py) that aims to support any compatible API.
1. [_Automated categorization_](https://beancount.github.io/docs/importing_external_data.html#automatic-categorization): With growing number of new transactions, manual categorization quickly becomes repetitive, boring and therefore error-prone. So, why not to leave the hard part for machines and then just tweak the details?
    * As the first step, Beanclerk provides a way to define rules for automated categorization.
    * The future step is to augment it by machine-learning capabilities (e.g. via integration of the [Smart Importer](https://github.com/beancount/smart_importer)). (Btw, it might be also interesting to use machine-learning to discover hidden patterns or to provide predictions about our financial behavior.)
1. _Automatic insertion of new transactions_: Beanclerk _appends_ new transactions to the Beancount input file (i.e. the ledger) defined in the configuration. It saves the step of doing this manually. (I don't care about the precise position of new transactions in the ledger because reporting tools like [Fava](https://github.com/beancount/fava) can sort them out anyway.) Consider to keep your ledger under a version control (e.g. via Git) to make any changes transparent and easy to review.

**Beanclerk is still a rather 'rough' prototype.** You may encounter some unhandled exceptions and the API may change significantly in the future.

**Beanclerk is currently tested on Linux only.**

### Existing importers

Currently, there is 1 built-in importer for [Fio banka](https://www.fio.cz/). I plan to add another for [Banka Creditas](https://www.creditas.cz/), and, maybe, for some crypto exchanges. (All importers may move into separate repos in the future so the user may install only those they actually need).

### Notes

I started Beanclerk primarily to try out some Python packages and to get better in software development by automating my daily workflow. Beanclerk does not aspire to be super inovative or unique. Actually, there are a couple of interesting projects of similar sort, which may provide inspiration or alternative solutions to the areas described above:

* [beancount-import](https://github.com/jbms/beancount-import): Web UI for semi-automatically importing external data into beancount.
* [finance-dl](https://github.com/jbms/finance-dl): Tools for automatically downloading/scraping personal financial data.
* [beancount_reds_importers](https://github.com/redstreet/beancount_reds_importers): Simple ingesting tools for Beancount (plain text, double entry accounting software). More importantly, a framework to allow you to easily write your own importers.
* [smart_importer](https://github.com/beancount/smart_importer): Augment Beancount importers with machine learning functionality.
* [autobean](https://github.com/SEIAROTg/autobean): A collection of plugins and scripts that help automating bookkeeping with beancount.

## Installation

Beanclerk requires Beancount, that may need some additional steps for its installation. See [Beancount Download & Installation](https://github.com/beancount/beancount#download--installation). Then, install Beanclerk via pip:

```
pip install beanclerk
```

Or, you may use [pipx](https://github.com/pypa/pipx) to install Beanclerk in an isolated environment:
```
pipx install beanclerk
```

Confirm successful installation by running:
```
bean-clerk -h
```

## Usage

### Configuration

Beanclerk needs a configuration file. By default, it searches for `beanclerk-config.yml` in the current working directory. Or, set a path to the config file via the `-c` (or `--config-file`) option. For the latest example of a config file, see [`tests/beanclerk-config.yml`](tests/beanclerk-config.yml).

### Running the import

Beanclerk currently implements a single command `import`. When running it for the first time, it is necessary to use at least the `--from-date` option to set the date to start the import from. (At the moment, Beanclerk runs import for all configured accounts.)

```
bean-clerk import --from-date 2023-01-01
```

Once Beanclerk encounters a transaction without a matching categorization rule, it prompts the user to resolve the situation:

```
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

## Contributing

Contributions are welcome. Make sure to create an issue first so we can discuss it.

Set up a development environment for playing with the source code:
```bash
./build_venv
source venv/bin/activate
pre-commit install  # https://pre-commit.com/
```

Run tests:
```bash
pytest
```

Follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/).
