"""Python build module."""

from builddrone.base_module import BaseModule
from builddrone.drone_exception import DroneException
from builddrone.runner import Runner


class PythonBuildModule(BaseModule):  # pylint: disable=too-few-public-methods
    """A module responsible for building the project.

    Blueprint configuration arguments:
        None
    """

    def run(self, runner: Runner, _args: dict) -> None:
        """Build the project with ``python -m build``.

        Args:
            runner: Runner instance used to execute commands.
            _args: Module configuration arguments. Unused.
        """
        runner.logger.info("Building...")
        exit_code = runner.run(["-m", "build"])

        if exit_code != 0:
            raise DroneException(f"Build failed with exit code {exit_code}")
