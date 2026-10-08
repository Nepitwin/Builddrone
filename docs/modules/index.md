# Modules

Builddrone ships with built-in modules registered by `ExecutionEngine`. Each
module is referenced by a dotted name in `blueprint.json`.

## Module groups

| Group | Modules |
| --- | --- |
| [AppVeyor](appveyor.md) | `appveyor.upload.tests`, `appveyor.upload.artifact` |
| [Archiver](archiver.md) | `archiver` |
| [Filesystem](filesystem.md) | `filesystem.copy`, `filesystem.cleanup` |
| [.NET](dotnet.md) | `dotnet.clean`, `dotnet.restore`, `dotnet.build`, `dotnet.pack`, `dotnet.nuget.push`, `dotnet.test` |
| [Python](python.md) | `python.venv`, `python.install`, `python.run`, `python.build`, `python.pylint` |
| [Robot Framework](robotframework.md) | `robotframework.test`, `robotframework.rebot` |
| [Twine](twine.md) | `twine.upload` |

Every module receives a `Runner` and a dictionary of arguments. The runner
executes commands with the currently selected Python interpreter and exposes
the blueprint's base directory for relative paths. Modules that call an
external program use `runner.run_command`.

## Custom modules

See [Using Builddrone as a framework](../framework.md) to register your own
modules alongside the built-in ones.
