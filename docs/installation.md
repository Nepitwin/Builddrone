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

To build the documentation locally:

```bash
python -m pip install -e ".[docs]"
mkdocs serve
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) to preview the site.
