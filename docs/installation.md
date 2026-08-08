# Installation

Install the latest released version from PyPI:

```bash
python -m pip install builddrone
```

For local development, install the project in editable mode together with its
development tools from the repository root:

```bash
python -m pip install -e ".[dev]"
```

Builddrone requires Python 3.8 or newer.

## Documentation

Published documentation is deployed to GitHub Pages for each release tag. Use
the version selector on the site to browse a specific release:

**https://nepitwin.github.io/Builddrone/**

The `latest` alias always points at the most recently published release.

Documentation is published with [mike](https://github.com/jimporter/mike) when a
release tag is pushed. GitHub Pages must be configured to deploy from the
`gh-pages` branch. To backfill docs for an older release, run the **Docs**
workflow manually and provide the tag name.

To build the documentation locally:

```bash
python -m pip install -e ".[docs]"
mkdocs serve
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) to preview the current
checkout. To preview versioned deployment locally:

```bash
mike serve
```
