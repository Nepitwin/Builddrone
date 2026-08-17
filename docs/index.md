# Builddrone

![Builddrone logo](https://raw.githubusercontent.com/Nepitwin/Builddrone/main/logo.png){ width="200" }

Builddrone is a JSON-driven build orchestration framework and command-line
interface for Python projects. A pipeline is made up of named stages, and each
stage executes an ordered list of registered modules.

## Links

- [GitHub](https://github.com/Nepitwin/Builddrone)
- [PyPI](https://pypi.org/project/builddrone/)

## Quick start

Install Builddrone, create a `blueprint.json`, and run a stage:

```bash
python -m pip install builddrone
python -m builddrone build
```

See [Installation](installation.md) and [Blueprint format](blueprint.md) for
details.

## Execution flow

```text
python -m builddrone <stage>
        |
        v
load blueprint.json -> select stage -> execute steps -> report failures
```

Any non-zero command exit code raises `DroneException` and stops the stage.
`robotframework.test` and `robotframework.rebot` are the exception: exit codes
1-250 mean tests failed, so later steps still run and the stage fails at the
end. Tool errors such as a missing file still stop immediately.

## License

MIT License
