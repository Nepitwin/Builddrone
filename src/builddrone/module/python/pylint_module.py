"""Python linting module."""

from builddrone.base_module import BaseModule
from builddrone.drone_exception import DroneException
from builddrone.runner import Runner


class PylintModule(BaseModule):  # pylint: disable=too-few-public-methods
    """A module responsible for running pylint.

    Blueprint configuration arguments:
        "paths": ["List of paths to lint"]
    """

    def run(self, runner: Runner, args: dict) -> None:
        runner.logger.info("Pylint...")
        paths = args.get("paths", [])

        if not isinstance(paths, list) or not paths:
            raise DroneException("No paths provided for pylint")

        exit_code = runner.run(["-m", "pylint", *paths])

        if exit_code != 0:
            raise DroneException(f"Pylint failed with exit code {exit_code}")
