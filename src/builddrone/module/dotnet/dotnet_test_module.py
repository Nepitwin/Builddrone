"""dotnet test module."""

from __future__ import annotations

from pathlib import Path

from builddrone.drone_exception import DroneException
from builddrone.module.dotnet.dotnet_base_module import DotnetBaseModule
from builddrone.module.dotnet.dotnet_projects import selected_project_files
from builddrone.path_safety import reject_symlink_component

_LOGGER_NAMES = {
    "nunit": "nunit",
    "xunit": "xunit",
}
_RESULTS_FILE = "TestResults.xml"
# Without --results-directory, the logger writes LogFileName into TestResults
# beside each project file.
_DEFAULT_RESULTS_DIRECTORY = "TestResults"


class DotnetTestModule(DotnetBaseModule):  # pylint: disable=too-few-public-methods
    """Run tests with ``dotnet test`` for NUnit or xUnit.

    The test project must reference the matching logger package:
    ``NunitXml.TestLogger`` for ``nunit``, or ``XunitXml.TestLogger`` for
    ``xunit``. ``framework`` is the target framework passed to ``--framework``.
    ``environment`` selects the test logger.

    Fails before ``dotnet test`` runs when ``TestResults.xml`` is a symlink,
    or when any directory leading to that file is a symlink. With
    ``results_directory``, that file is inside the configured directory.
    Otherwise it is ``TestResults/TestResults.xml`` beside the project file.

    Blueprint configuration arguments:
        "environment": "Required test environment: nunit or xunit"
        "project": "Optional project or solution path"
        "configuration": "Optional build configuration, such as Release"
        "framework": "Optional target framework, such as net10.0"
        "filter": "Optional test filter expression"
        "results_directory": "Optional directory for TestResults.xml"
        "verbosity": "Optional dotnet verbosity level"
        "no_build": "Skip building before testing"
        "no_restore": "Skip restore before testing"
    """

    log_message = "Testing..."
    failure_label = "Test"

    def _build_arguments(self, args: dict, base_path: Path) -> list[str]:
        logger_name = self._logger_name(args)
        command = ["test"]
        self._append_project(command, args, base_path)
        self._append_configuration(command, args)
        self._append_framework(command, args)
        self._append_verbosity(command, args)
        self._append_switch(command, args, "no_build", "--no-build")
        self._append_switch(command, args, "no_restore", "--no-restore")

        test_filter = self._optional_string(args, "filter")
        if test_filter is not None:
            command.extend(["--filter", test_filter])

        self._append_logger(command, args, base_path, logger_name)
        return command

    @staticmethod
    def _logger_name(args: dict) -> str:
        """Return the logger name selected by ``environment``."""
        environment = args.get("environment")
        if not isinstance(environment, str) or not environment.strip():
            raise DroneException("Argument 'environment' must be 'nunit' or 'xunit'")
        logger_name = _LOGGER_NAMES.get(environment)
        if logger_name is None:
            raise DroneException("Argument 'environment' must be 'nunit' or 'xunit'")
        return logger_name

    def _append_logger(
        self, command: list[str], args: dict, base_path: Path, logger_name: str
    ) -> None:
        """Append the results directory and environment-specific logger."""
        results_directory = self._directory_argument(
            args, base_path, "results_directory", "Results directory"
        )
        if results_directory is None:
            logger = f"{logger_name};LogFileName={_RESULTS_FILE}"
            results_files = self._default_results_files(args, base_path)
        else:
            command.extend(["--results-directory", results_directory])
            results_files = [Path(results_directory) / _RESULTS_FILE]
            logger = f"{logger_name};LogFilePath={results_files[0]}"
        for results_file in results_files:
            reject_symlink_component(results_file, base_path, "Results file")
        command.extend(["--logger", logger])

    def _default_results_files(self, args: dict, base_path: Path) -> list[Path]:
        """Return ``TestResults/TestResults.xml`` beside each selected project."""
        projects = selected_project_files(
            self._project_path(args, base_path), base_path
        )
        return [
            project.parent / _DEFAULT_RESULTS_DIRECTORY / _RESULTS_FILE
            for project in projects
        ]
