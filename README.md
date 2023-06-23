# Beanclerk

**CURRENT STATUS: NOT A WORKING PROTOTYPE YET (WORK IN PROGRESS)**

Beanclerk is an extension for the double-entry bookkeeping software [Beancount](https://github.com/beancount/beancount) with the goal to automate some repetitive and error-prone tasks not addressed by the Beancount itself, namely:

1. [Network downloads](https://beancount.github.io/docs/importing_external_data.html#automating-network-downloads): As some banks and exchanges provide public APIs to their services, it's easier to use these APIs instead of a manual download of CSV (or similar) files followed by a multi-step import process. Also it might be interesting to provide some equivalent of the [importer protocol](https://beancount.github.io/docs/importing_external_data.html#writing-an-importer) for APIs.
1. [Categorization of new transactions](https://beancount.github.io/docs/importing_external_data.html#automatic-categorization): I cannot agree with the author of Beancount that manual categorization is "a breeze" and automated solution is not needed. The repetitiveness of manual categorization is sometimes annoying and therefore prone to inconsistencies and errors. Let's leave the hard part for machines and then just tweak the details.

## Development

```
make venv  # see the note below
source venv/bin/activate
```

> Installation of the `beancount` package may require to install `gcc` and the header files and configuration needed to compile Python extension modules (e.g. `python3-devel` package on Fedora Linux).

Uses [pre-commit](https://pre-commit.com/).

Use [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/).

Types:
* `fix`: patches a bug in the codebase.
* `feat`: introduces a new feature to the codebase.
* `refactor`: neither fixes a bug nor adds a feature.
* `perf`: improves performance.
* `docs`: makes documentation only changes.
* `test`: adds missing tests or corrects existing tests.

Scopes (optional):
* `package`: a change related to Python packaging and distribution.
* `repo`: a change related to Git or development tooling.
