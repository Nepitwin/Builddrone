"""Python linting module."""

from builddrone.base_module import BaseModule
from builddrone.drone_exception import DroneException
from builddrone.runner import Runner


class PylintModule(BaseModule):  # pylint: disable=too-few-public-methods
    """A module responsible for running pylint.

    Blueprint configuration arguments:
        "paths": ["List of paths to lint"]
        "files": ["Optional list of individual Python files to lint"]
        "ignore": ["Optional list of file or directory base names to skip"]
    """

    def run(self, runner: Runner, args: dict) -> None:
        runner.logger.info("Pylint...")
        paths = args.get("paths", [])
        files = args.get("files", [])
        ignore = args.get("ignore", [])

        if not isinstance(paths, list) or not all(
            isinstance(item, str) and item for item in paths
        ):
            raise DroneException("Paths must be a list of non-empty strings")

        if not isinstance(files, list) or not all(
            isinstance(item, str) and item for item in files
        ):
            raise DroneException("Files must be a list of non-empty strings")

        if not paths and not files:
            raise DroneException("No paths or files provided for pylint")

        if not isinstance(ignore, list) or not all(
            isinstance(item, str) and item for item in ignore
        ):
            raise DroneException("Ignore must be a list of non-empty strings")

        command = ["-m", "pylint"]
        if ignore:
            command.extend(["--ignore", ",".join(ignore)])
        command.extend([*paths, *files])

        exit_code = runner.run(command, cwd=str(runner.get_base_path()))

        if exit_code != 0:
            raise DroneException(f"Pylint failed with exit code {exit_code}")
