# AppVeyor modules

[![AppVeyor build](https://ci.appveyor.com/api/projects/status/github/Nepitwin/Builddrone?branch=main&svg=true)](https://ci.appveyor.com/project/github/nepitwin/builddrone)

## `appveyor.upload.tests`

Upload JUnit or xUnit XML results files to the AppVeyor test-results API.

| Argument | Required | Description |
| --- | --- | --- |
| `sources` | yes | Non-empty list of results file paths |
| `repeat` | no | Max upload attempts per file (default: `1`) |
| `timeout` | no | Seconds between failed attempts (default: `10`) |

`sources` entries can be plain path strings or objects with `source` and
optional `format` (`junit` or `xunit`). When `format` is omitted, the upload
endpoint is chosen from the XML root element:

- `<assemblies>` → xUnit
- `<testsuite>` or `<testsuites>` → JUnit

The job id is read from the `APPVEYOR_JOB_ID` environment variable.

### Example

```json
{
  "module": "appveyor.upload.tests",
  "args": {
    "sources": ["result/xunit.xml", "result/junit.xml"],
    "repeat": 5,
    "timeout": 10
  }
}
```

### Explicit format override

```json
{
  "module": "appveyor.upload.tests",
  "args": {
    "sources": [
      {"source": "results/xunit.xml", "format": "xunit"},
      {"source": "results/junit.xml", "format": "junit"}
    ]
  }
}
```

### Build status badge

Add a build status badge to your README:

```markdown
[![AppVeyor build](https://ci.appveyor.com/api/projects/status/github/Nepitwin/Builddrone?branch=main&svg=true)](https://ci.appveyor.com/project/github/nepitwin/builddrone)
```

See the [AppVeyor example](../examples/appveyor.md) for a full CI setup.
