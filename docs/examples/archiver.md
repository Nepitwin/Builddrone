# Archiver example

The archiver example in `example/archiver` creates sample output files and
builds zip archives from a folder and from individual files.

## Run locally

```bash
cd example/archiver
python -m builddrone archive
python -m builddrone cleanup
```

The `archive` stage:

1. Runs `main.py` with `python.run` to create `result/summary.txt` and `result/nested/data.txt`
2. Creates `result.zip` from the `result` folder with `archiver`
3. Creates `summary.zip` from `result/summary.txt` with `archiver`

The `cleanup` stage removes the `result` folder and both zip files.

## Blueprint

See [`example/archiver/blueprint.json`](https://github.com/Nepitwin/Builddrone/blob/main/example/archiver/blueprint.json)
in the repository.

## Related modules

- [Archiver module](../modules/archiver.md)
