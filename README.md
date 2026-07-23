# Builddrone

Builddrone is a JSON-driven build orchestration framework and command-line
interface for Python projects. A pipeline is made up of named stages, and each
stage executes an ordered list of registered modules.

## Installation

Install the project and its development tools from the repository root:

```bash
python -m pip install -e ".[dev]"
```

Builddrone requires Python 3.10 or newer.

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

## Built-in modules

### Filesystem

| Module | Arguments | Purpose |
| --- | --- | --- |
| `filesystem.copy` | `source`, `destination` | Copy a directory tree. |
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

Both Robot Framework modules accept an `arguments` dictionary and an optional
`cwd`:

| Module | Purpose |
| --- | --- |
| `robotframework.test` | Run `python -m robot`. |
| `robotframework.rebot` | Run `python -m robot.rebot` to post-process results. |

Dictionary values are converted to command-line arguments. A `null` value is a
flag or positional argument, a string receives a following value, and a list
receives multiple values:

```json
{
  "module": "robotframework.test",
  "args": {
    "arguments": {
      "--outputdir": "results",
      "tests": null
    }
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
