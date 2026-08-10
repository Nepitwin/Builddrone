# AppVeyor modules

[![AppVeyor build](https://ci.appveyor.com/api/projects/status/github/Nepitwin/Builddrone?branch=main&svg=true)](https://ci.appveyor.com/project/Nepitwin/builddrone)

## `appveyor.upload.tests`

Upload JUnit or xUnit XML results files to the AppVeyor test-results API.

| Argument | Required | Description |
| --- | --- | --- |
| `sources` | yes | Non-empty list of objects with `file` and `type` |
| `repeat` | no | Max upload attempts per file (default: `1`) |
| `timeout` | no | Seconds between failed attempts (default: `10`) |

Each `sources` entry must be an object with:

- `file` — path to the XML results file
- `type` — `junit` or `xunit`

The job id is read from the `APPVEYOR_JOB_ID` environment variable.

### Example

```json
{
  "module": "appveyor.upload.tests",
  "args": {
    "sources": [
      {"file": "results/xunit.xml", "type": "xunit"},
      {"file": "results/junit.xml", "type": "junit"}
    ],
    "repeat": 5,
    "timeout": 10
  }
}
```

## `appveyor.upload.artifact`

Upload build artifacts to AppVeyor using `Push-AppveyorArtifact`.

| Argument | Required | Description |
| --- | --- | --- |
| `files` | yes | Non-empty list of artifact file paths |

Each file is uploaded with its basename as the AppVeyor artifact name. This
module runs on AppVeyor workers where the `Push-AppveyorArtifact` PowerShell
cmdlet is available.

### Example

```json
{
  "module": "appveyor.upload.artifact",
  "args": {
    "files": ["results.zip"]
  }
}
```

### Archive and upload failure artifacts

Use two steps in a blueprint stage:

```json
[
  {
    "module": "archiver",
    "args": {
      "filename": "results.zip",
      "folders": ["result"]
    }
  },
  {
    "module": "appveyor.upload.artifact",
    "args": {
      "files": ["results.zip"]
    }
  }
]
```

See the [AppVeyor example](../examples/appveyor.md) for a full CI setup.
