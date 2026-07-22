"""Python run module."""

from builddrone.base_module import BaseModule
from builddrone.drone_exception import DroneException
from builddrone.runner import Runner


class PythonRunModule(BaseModule):  # pylint: disable=too-few-public-methods
    """A module responsible for running Python source files.

    Blueprint configuration arguments:
        "source": "Python file to execute"
    """

    def run(self, runner: Runner, args: dict) -> None:
        """Run a Python source file with the configured interpreter.

        Args:
            runner: Runner instance used to execute commands.
            args: Module configuration arguments.
        """
        runner.logger.info("Running...")
        source = args.get("source")

        if not isinstance(source, str) or not source:
            raise DroneException("No source provided for run")

        exit_code = runner.run([source], cwd=str(runner.get_base_path()))

        if exit_code != 0:
            raise DroneException(f"Run failed with exit code {exit_code}")
