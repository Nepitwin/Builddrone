# Python example

The Python example in `example/python` creates a virtual environment, installs
requirements, lints and runs `main.py`, and builds a wheel and source
distribution with `python -m build`.

## Run locally

```bash
cd example/python
python -m builddrone build
python -m builddrone cleanup
```

The `build` stage:

1. Creates `.venv` with `python.venv`
2. Installs `requirements.txt` with `python.install`
3. Runs Pylint with `python.pylint`
4. Runs `main.py` with `python.run`
5. Builds packages with `python.build`

The `cleanup` stage removes `.venv`, egg-info, and `dist`.

## Blueprint

See [`example/python/blueprint.json`](https://github.com/Nepitwin/Builddrone/blob/main/example/python/blueprint.json)
in the repository.
