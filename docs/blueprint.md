# Blueprint format

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

Stage names are arbitrary. Examples in this repository use names such as
`build`, `test`, `upload`, and `cleanup`.
