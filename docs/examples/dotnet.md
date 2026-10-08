# .NET example

The .NET example in `example/dotnet` restores, builds, and tests a class
library with NUnit and xUnit, then packs a NuGet package. It targets
`net10.0`.

## Run locally

```bash
cd example/dotnet
python -m builddrone build
python -m builddrone clean
python -m builddrone cleanup
```

The `build` stage:

1. Restores `Builddrone.DotnetExample.slnx` with `dotnet.restore`
2. Builds the solution in `Release` with `dotnet.build`
3. Runs NUnit tests with `dotnet.test`
4. Runs xUnit tests with `dotnet.test`
5. Packs the class library with `dotnet.pack`

The `clean` stage runs `dotnet clean` for the Release configuration.

The `cleanup` stage removes `artifacts`, `results`, and the `bin` and `obj`
folders.

## Deploy

The `deploy` stage pushes `artifacts/*.nupkg` with `dotnet.nuget.push`. Set
`NUGET_API_KEY` before running it. Gate that stage in CI so it runs only for
tagged builds.

```bash
cd example/dotnet
python -m builddrone deploy
```

## Blueprint

See [`example/dotnet/blueprint.json`](https://github.com/Nepitwin/Builddrone/blob/main/example/dotnet/blueprint.json)
in the repository.

## Related modules

- [.NET modules](../modules/dotnet.md)
