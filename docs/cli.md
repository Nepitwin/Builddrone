# Command-line usage

Run a stage from the directory containing its blueprint:

```bash
python -m builddrone <stage>
```

Replace `<stage>` with a top-level key from `blueprint.json`, for example
`build`, `test`, or `cleanup`.

## Examples

| Example | Command |
| --- | --- |
| [Python](examples/python.md) | `python -m builddrone build` |
| [Robot Framework](examples/robotframework.md) | `python -m builddrone test` |
| [AppVeyor](examples/appveyor.md) | `python -m builddrone upload` |

Each example directory includes its own `blueprint.json` and a `cleanup`
stage to remove temporary artifacts.
