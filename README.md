# Builddrone

<table>
  <tr>
    <td rowspan="2" valign="middle">
      <img src="https://raw.githubusercontent.com/Nepitwin/Builddrone/main/logo.png" alt="Builddrone" width="200" height="200">
    </td>
    <td><strong>Project</strong></td>
    <td><a href="https://github.com/Nepitwin/Builddrone">GitHub</a> · <a href="https://pypi.org/project/builddrone/">PyPI</a></td>
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

## Installation

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

## Blueprint format

Builddrone loads `blueprint.json` from the current working directory. The
top-level keys are stage names, and each stage contains module steps:

```json
{
  "build": [
    {
      "module": "python.venv",
      "args": {"source": ".venv"}
    },
    {
      "module": "python.install",
      "args": {"requirements": "requirements.txt"}
    },
    {
      "module": "python.run",
      "args": {"source": "main.py"}
    }
  ]
}
```

Relative paths are resolved from the directory containing `blueprint.json`.
Each step runs only after the preceding step succeeds.

## Command-line usage

Run a stage from the directory containing its blueprint:

```bash
cd example/python
python -m builddrone build
python -m builddrone cleanup
```

The Python example creates `.venv` automatically, installs its requirements,
lints and runs `main.py`, and builds a wheel and source distribution with
`python -m build`. The separate `cleanup` stage removes the temporary
environment and generated build artifacts.

The Robot Framework example runs similarly:

```bash
cd example/robotframework
python -m builddrone test
python -m builddrone cleanup
```

Its `robotframework.test` step writes `results/output.xml`, and
`robotframework.rebot` converts that result into reports under
`results/rebot`.

The AppVeyor example uploads sample JUnit and xUnit XML files:

```bash
cd example/appveyor
python -m builddrone upload
python -m builddrone cleanup
```

The `upload` stage regenerates `results/xunit.xml` and `results/junit.xml`,
then posts them to the AppVeyor test-results API. Set `APPVEYOR_JOB_ID` to
the current AppVeyor job id before running the stage; AppVeyor sets this
variable automatically in CI.

To run the example on AppVeyor, connect the repository and set **Custom
configuration .yml file name** to `example/appveyor/appveyor.yml` in the
project settings. The build installs Builddrone, runs the `upload` stage from
`example/appveyor/blueprint.json`, and then runs `cleanup`.

## Built-in modules

### AppVeyor

| Module | Arguments | Purpose |
| --- | --- | --- |
| `appveyor.upload.tests` | `sources`, optional `repeat`, optional `timeout` | Upload JUnit/xUnit XML files to the AppVeyor test-results API. |

`sources` is a non-empty list of results file paths (relative to the blueprint directory, or absolute).
Each file is uploaded in order. `repeat` is the maximum number of upload attempts per file and defaults to `1`.
`timeout` is the number of seconds to wait between failed attempts and defaults to `10`.
The job id is read from the `APPVEYOR_JOB_ID` environment variable.

```json
{
  "module": "appveyor.upload.tests",
  "args": {
    "sources": ["result/xunit.xml", "result/junit.xml"],
    "repeat": 5,
    "timeout": 10
  }
}
```

### Filesystem

| Module | Arguments | Purpose |
| --- | --- | --- |
| `filesystem.copy` | `source`, `destination`, optional `files` | Copy a directory tree, optionally filtering files with a glob such as `*.jpg`. |
| `filesystem.cleanup` | `files`, `folders` | Remove listed files and folders. |

### Python

| Module | Arguments | Purpose |
| --- | --- | --- |
| `python.venv` | `source` | Select an environment, creating it with pip if needed. An empty source resets the runner. |
| `python.install` | `requirements` or `source` | Install requirements or a package with pip. |
| `python.run` | `source` | Run a Python source file. |
| `python.build` | none | Run `python -m build`. |
| `python.pylint` | `paths`, `files`, `ignore` | Run Pylint against paths or individual files. |

### Robot Framework

Both Robot Framework modules accept an ordered `arguments` list and an
optional `cwd`:

| Module | Purpose |
| --- | --- |
| `robotframework.test` | Run `python -m robot`. |
| `robotframework.rebot` | Run `python -m robot.rebot` to post-process results. |

Each string in the list is emitted as a standalone command-line argument. Each
single-entry object is emitted as a key followed by its value; list values
emit the key followed by multiple values, and boolean `true` emits only the
key. This keeps positional arguments explicit and avoids using `null` as a
sentinel:

```json
{
  "module": "robotframework.test",
  "args": {
    "arguments": [
      {"--outputdir": "results"},
      "tests"
    ]
  }
}
```

## Using Builddrone as a framework

Built-in modules are registered by `ExecutionEngine`. Custom modules can be
added by passing them to the constructor:

```python
from builddrone.base_module import BaseModule
from builddrone.execution_engine import ExecutionEngine


class GreetingModule(BaseModule):
    def run(self, runner, args):
        runner.logger.info("Hello from %s", args.get("name", "Builddrone"))


engine = ExecutionEngine({"custom.greeting": GreetingModule()})
engine.run("build")
```

The custom module can then be used in `blueprint.json`:

```json
{
  "build": [
    {
      "module": "custom.greeting",
      "args": {"name": "Builddrone"}
    }
  ]
}
```

Every module receives a `Runner` and a dictionary of arguments. The runner
executes commands with the currently selected Python interpreter and exposes
the blueprint's base directory for relative paths.

## Execution flow

```text
python -m builddrone <stage>
        |
        v
load blueprint.json -> select stage -> execute steps -> report failures
```

Any non-zero command exit code raises `DroneException` and stops the stage.

## License

MIT License
