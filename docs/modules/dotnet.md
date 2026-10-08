# .NET modules

These modules run the `dotnet` CLI. Relative paths are resolved from the
directory that contains `blueprint.json`. A missing `dotnet` executable stops
the stage.

`dotnet.test` chooses an NUnit or xUnit logger. The test project must
reference `NunitXml.TestLogger` or `XunitXml.TestLogger` for that logger to
write `TestResults.xml`. A non-zero `dotnet test` exit code stops the stage.

## `dotnet.clean`

Run `dotnet clean`.

| Argument | Required | Description |
| --- | --- | --- |
| `project` | no | Project or solution path |
| `configuration` | no | Build configuration, such as `Release` |
| `framework` | no | Target framework, such as `net10.0` |
| `runtime` | no | Runtime identifier |
| `output` | no | Output directory |
| `verbosity` | no | `q`, `m`, `n`, `d`, `diag`, or the long form of those levels |

### Example

```json
{
  "module": "dotnet.clean",
  "args": {
    "project": "Builddrone.DotnetExample.slnx",
    "configuration": "Release"
  }
}
```

## `dotnet.restore`

Run `dotnet restore`.

| Argument | Required | Description |
| --- | --- | --- |
| `project` | no | Project or solution path |
| `sources` | no | List of NuGet sources |
| `runtime` | no | Runtime identifier |
| `verbosity` | no | Verbosity level |
| `force` | no | Pass `--force` when `true` |

### Example

```json
{
  "module": "dotnet.restore",
  "args": {
    "project": "Builddrone.DotnetExample.slnx",
    "sources": ["https://api.nuget.org/v3/index.json"]
  }
}
```

## `dotnet.build`

Run `dotnet build`.

| Argument | Required | Description |
| --- | --- | --- |
| `project` | no | Project or solution path |
| `configuration` | no | Build configuration, such as `Release` |
| `framework` | no | Target framework, such as `net10.0` |
| `runtime` | no | Runtime identifier |
| `output` | no | Output directory |
| `verbosity` | no | Verbosity level |
| `no_restore` | no | Skip restore when `true` |

### Example

```json
{
  "module": "dotnet.build",
  "args": {
    "project": "Builddrone.DotnetExample.slnx",
    "configuration": "Release",
    "no_restore": true
  }
}
```

## `dotnet.pack`

Build a NuGet package with `dotnet pack`.

| Argument | Required | Description |
| --- | --- | --- |
| `project` | no | Project or solution path |
| `configuration` | no | Build configuration, such as `Release` |
| `output` | no | Directory for the generated package |
| `verbosity` | no | Verbosity level |
| `version_suffix` | no | Pre-release version suffix |
| `no_build` | no | Skip the build when `true` |
| `no_restore` | no | Skip restore when `true` |
| `include_symbols` | no | Create a symbols package when `true` |
| `include_source` | no | Include sources in the symbols package when `true` |

### Example

```json
{
  "module": "dotnet.pack",
  "args": {
    "project": "src/Builddrone.DotnetExample/Builddrone.DotnetExample.csproj",
    "configuration": "Release",
    "output": "artifacts"
  }
}
```

## `dotnet.nuget.push`

Deploy packages with `dotnet nuget push`. Each entry in `packages` is a glob
pattern. Matching `.nupkg` and `.snupkg` files are pushed one at a time.

The API key is read from the environment variable named by `api_key_env`.
Do not put the key in `blueprint.json`. Tag-based deployment should be handled
outside this module, for example by running the deploy stage only on tagged
CI builds.

| Argument | Required | Description |
| --- | --- | --- |
| `packages` | yes | Non-empty list of glob patterns |
| `source` | yes | NuGet source URL or name |
| `api_key_env` | yes | Environment variable that holds the API key |
| `skip_duplicate` | no | Skip packages that already exist (default: `true`) |
| `symbol_source` | no | Symbol server URL or name |
| `symbol_api_key_env` | no | Environment variable that holds the symbol server key |

### Example

```json
{
  "module": "dotnet.nuget.push",
  "args": {
    "packages": ["artifacts/*.nupkg"],
    "source": "https://api.nuget.org/v3/index.json",
    "api_key_env": "NUGET_API_KEY",
    "skip_duplicate": true
  }
}
```

## `dotnet.test`

Run `dotnet test`. `environment` selects the logger. `framework` is the target
framework passed to `--framework`, not the test environment.

| Argument | Required | Description |
| --- | --- | --- |
| `environment` | yes | `nunit` or `xunit` |
| `project` | no | Project or solution path |
| `configuration` | no | Build configuration, such as `Release` |
| `framework` | no | Target framework, such as `net10.0` |
| `filter` | no | Test filter expression |
| `results_directory` | no | Directory for `TestResults.xml` |
| `verbosity` | no | Verbosity level |
| `no_build` | no | Skip the build when `true` |
| `no_restore` | no | Skip restore when `true` |

### NUnit

```json
{
  "module": "dotnet.test",
  "args": {
    "project": "tests/Builddrone.DotnetExample.NUnitTests/Builddrone.DotnetExample.NUnitTests.csproj",
    "environment": "nunit",
    "configuration": "Release",
    "results_directory": "results/nunit"
  }
}
```

### xUnit

```json
{
  "module": "dotnet.test",
  "args": {
    "project": "tests/Builddrone.DotnetExample.XUnitTests/Builddrone.DotnetExample.XUnitTests.csproj",
    "environment": "xunit",
    "configuration": "Release",
    "results_directory": "results/xunit"
  }
}
```

See the [.NET example](../examples/dotnet.md) for a full restore, build, test,
pack, and deploy pipeline.
