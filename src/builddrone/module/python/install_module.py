"""Python install module."""

from builddrone.base_module import BaseModule
from builddrone.drone_exception import DroneException
from builddrone.runner import Runner


class PythonInstallModule(BaseModule):  # pylint: disable=too-few-public-methods
    """A module responsible for installing Python packages.

    Blueprint configuration arguments:
        "source": "Package source to install"
    """

    def run(self, runner: Runner, args: dict) -> None:
        """Install a package source with ``python -m pip install``.

        Args:
            runner: Runner instance used to execute commands.
            args: Module configuration arguments.
        """
        runner.logger.info("Installing...")
        source = args.get("source")

        if not isinstance(source, str) or not source:
            raise DroneException("No source provided for install")

        exit_code = runner.run(["-m", "pip", "install", source])

        if exit_code != 0:
            raise DroneException(f"Install failed with exit code {exit_code}")
