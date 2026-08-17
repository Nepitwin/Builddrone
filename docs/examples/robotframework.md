# Robot Framework example

The Robot Framework example in `example/robotframework` runs a test suite and
post-processes the results with rebot.

## Run locally

```bash
cd example/robotframework
python -m builddrone test
python -m builddrone cleanup
```

The `test` stage:

1. Creates `.venv` and installs `requirements.txt`
2. Runs `robotframework.test`, writing `results/output.xml`
3. Runs `robotframework.rebot`, producing reports under `results/rebot`

Failed tests (exit codes 1-250) do not stop the stage immediately, so rebot
can still post-process results. The stage then fails after all steps complete.

The `cleanup` stage removes `.venv` and `results`.

## Blueprint

See [`example/robotframework/blueprint.json`](https://github.com/Nepitwin/Builddrone/blob/main/example/robotframework/blueprint.json)
in the repository.

## Related modules

- [Robot Framework modules](../modules/robotframework.md)
