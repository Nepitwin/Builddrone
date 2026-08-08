# Using Builddrone as a framework

Built-in modules are registered by `ExecutionEngine`. Custom modules can be
added by passing them to the constructor:

```python
from builddrone.base_module import BaseModule
from builddrone.execution_engine import ExecutionEngine


class GreetingModule(BaseModule):
    def run(self, runner, args):
        runner.logger.info("Hello from %s", args.get("name", "Builddrone"))


engine = ExecutionEngine({"custom.greeting": GreetingModule()})
engine.run("build")
```

The custom module can then be used in `blueprint.json`:

```json
{
  "build": [
    {
      "module": "custom.greeting",
      "args": {"name": "Builddrone"}
    }
  ]
}
```

## Module contract

Every module receives a `Runner` and a dictionary of arguments. The runner
executes commands with the currently selected Python interpreter and exposes
the blueprint's base directory for relative paths.

Implement `run(self, runner: Runner, args: dict) -> None` on a subclass of
`BaseModule`. Raise `DroneException` to stop the stage with a clear error
message.

## Built-in registration

`ExecutionEngine` registers these modules automatically when they are not
already present in the constructor dictionary:

| Module name |
| --- |
| `appveyor.upload.artifact` |
| `appveyor.upload.tests` |
| `archiver` |
| `filesystem.cleanup` |
| `filesystem.copy` |
| `python.build` |
| `python.install` |
| `python.run` |
| `python.venv` |
| `python.pylint` |
| `robotframework.test` |
| `robotframework.rebot` |
| `twine.upload` |

Pass a module with the same name in the constructor dictionary to override a
built-in implementation.
