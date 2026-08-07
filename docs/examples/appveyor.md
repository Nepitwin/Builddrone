# AppVeyor example

The AppVeyor example in `example/appveyor` generates sample JUnit and xUnit
XML files and uploads them to the AppVeyor test-results API.

## Run locally

```bash
cd example/appveyor
python -m builddrone upload
python -m builddrone cleanup
```

The `upload` stage:

1. Runs `main.py` to regenerate `results/xunit.xml` and `results/junit.xml`
2. Uploads both files with `appveyor.upload.tests`

Set `APPVEYOR_JOB_ID` to the current AppVeyor job id before running the stage.
AppVeyor sets this variable automatically in CI.

The `cleanup` stage removes the `results` folder.

## Run on AppVeyor

1. Connect the repository in AppVeyor
2. Set **Custom configuration .yml file name** to `example/appveyor/appveyor.yml`
3. Start a build

The CI configuration installs Builddrone, runs the `upload` stage, and then
runs `cleanup`.

## Blueprint

See [`example/appveyor/blueprint.json`](https://github.com/Nepitwin/Builddrone/blob/main/example/appveyor/blueprint.json)
and [`example/appveyor/appveyor.yml`](https://github.com/Nepitwin/Builddrone/blob/main/example/appveyor/appveyor.yml)
in the repository.

## Related modules

- [AppVeyor modules](../modules/appveyor.md)
