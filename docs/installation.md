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

**https://nepitwin.github.io/Builddrone/latest/**

The `latest` alias always points at the most recently published release.

Documentation is published with [mike](https://github.com/jimporter/mike) when a
release tag is pushed. The Docs workflow builds the versioned site onto the
existing `gh-pages` history and pushes that commit. GitHub Pages deploys the
branch. In the repository Pages settings, set the source to **Deploy from a
branch** and select `gh-pages`.

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
