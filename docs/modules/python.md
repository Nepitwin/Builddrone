# Python modules

## `python.venv`

Select a Python virtual environment, creating it with pip if needed. An empty
`source` resets the runner to the system interpreter.

| Argument | Required | Description |
| --- | --- | --- |
| `source` | yes | Path to the virtual environment |

### Example

```json
{
  "module": "python.venv",
  "args": {
    "source": ".venv"
  }
}
```

## `python.install`

Install requirements or a package with pip.

| Argument | Required | Description |
| --- | --- | --- |
| `requirements` | one of | Path to a requirements file |
| `source` | one of | Package or source directory to install |

### Example

```json
{
  "module": "python.install",
  "args": {
    "requirements": "requirements.txt"
  }
}
```

## `python.run`

Run a Python source file with the configured interpreter.

| Argument | Required | Description |
| --- | --- | --- |
| `source` | yes | Python file to execute |

### Example

```json
{
  "module": "python.run",
  "args": {
    "source": "main.py"
  }
}
```

## `python.build`

Run `python -m build` to produce wheel and source distribution artifacts.

This module accepts no arguments.

### Example

```json
{
  "module": "python.build",
  "args": {}
}
```

## `python.pylint`

Run Pylint against paths or individual files.

| Argument | Required | Description |
| --- | --- | --- |
| `paths` | no | Directories to lint |
| `files` | no | Individual files to lint |
| `ignore` | no | Paths to exclude |

### Example

```json
{
  "module": "python.pylint",
  "args": {
    "paths": ["."],
    "ignore": [".venv"]
  }
}
```

See the [Python example](../examples/python.md) for a full build pipeline using
these modules.
