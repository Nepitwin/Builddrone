# AppVeyor example

The AppVeyor example in `example/appveyor` generates sample JUnit and xUnit
XML files, uploads them to the AppVeyor test-results API, archives the
results folder, and uploads the zip as a build artifact.

## Run locally

```bash
cd example/appveyor
python -m builddrone upload
python -m builddrone artifacts
python -m builddrone cleanup
```

The `upload` stage:

1. Runs `main.py` with `python.run` to regenerate `results/xunit.xml` and `results/junit.xml`
2. Uploads both files with `appveyor.upload.tests`

The `artifacts` stage:

1. Creates `results.zip` from the `results` folder with `archiver`
2. Uploads the zip with `appveyor.upload.artifact`

Set `APPVEYOR_JOB_ID` to the current AppVeyor job id before running the
`upload` stage. AppVeyor sets this variable automatically in CI. The
`artifacts` stage requires an AppVeyor worker with the
`Push-AppveyorArtifact` PowerShell cmdlet.

The `cleanup` stage removes the `results` folder and `results.zip`.

## Run on AppVeyor

1. Connect the repository in AppVeyor
2. Set **Custom configuration .yml file name** to `example/appveyor/appveyor.yml`
3. Start a build

The CI configuration installs Builddrone, runs the `upload` stage, archives
and uploads the results zip with `artifacts`, and then runs `cleanup`.

## Blueprint

See [`example/appveyor/blueprint.json`](https://github.com/Nepitwin/Builddrone/blob/main/example/appveyor/blueprint.json)
and [`example/appveyor/appveyor.yml`](https://github.com/Nepitwin/Builddrone/blob/main/example/appveyor/appveyor.yml)
in the repository.

## Related modules

- [AppVeyor modules](../modules/appveyor.md)
- [Archiver module](../modules/archiver.md)
