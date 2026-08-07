# Builddrone

<table>
  <tr>
    <td rowspan="2" valign="middle">
      <img src="https://raw.githubusercontent.com/Nepitwin/Builddrone/main/logo.png" alt="Builddrone" width="200" height="200">
    </td>
    <td><strong>Project</strong></td>
    <td><a href="https://github.com/Nepitwin/Builddrone">GitHub</a> · <a href="https://pypi.org/project/builddrone/">PyPI</a> · <a href="https://nepitwin.github.io/Builddrone/">Documentation</a></td>
  </tr>
  <tr>
    <td><strong>Environment</strong></td>
    <td>
      <a href="https://pypi.org/project/builddrone/"><img src="https://img.shields.io/pypi/v/builddrone.svg" alt="PyPI version"></a>
      <a href="https://github.com/Nepitwin/Builddrone/actions/workflows/workflow.yml"><img src="https://github.com/Nepitwin/Builddrone/actions/workflows/workflow.yml/badge.svg" alt="Tests"></a>
    </td>
  </tr>
</table>

Builddrone is a JSON-driven build orchestration framework and command-line
interface for Python projects. A pipeline is made up of named stages, and each
stage executes an ordered list of registered modules.

## Documentation

Full documentation is published on GitHub Pages:

**https://nepitwin.github.io/Builddrone/**

Topics covered there include installation, blueprint format, CLI usage, all
built-in modules, examples, and custom module development.

## Quick start

Install from PyPI, create a `blueprint.json`, and run a stage:

```bash
python -m pip install builddrone
python -m builddrone build
```

For local development:

```bash
python -m pip install -e ".[dev]"
```

Builddrone requires Python 3.8 or newer.

## Examples

| Example | Directory | Stage |
| --- | --- | --- |
| Python | `example/python` | `build` |
| Robot Framework | `example/robotframework` | `test` |
| AppVeyor | `example/appveyor` | `upload` |

See the [documentation](https://nepitwin.github.io/Builddrone/) for details
on each example and all available modules.

## License

MIT License
