"""dotnet clean module."""

from __future__ import annotations

from pathlib import Path

from builddrone.module.dotnet.dotnet_base_module import DotnetBaseModule


class DotnetCleanModule(DotnetBaseModule):  # pylint: disable=too-few-public-methods
    """Clean a .NET project or solution with ``dotnet clean``.

    Blueprint configuration arguments:
        "project": "Optional project or solution path"
        "configuration": "Optional build configuration, such as Release"
        "framework": "Optional target framework, such as net10.0"
        "runtime": "Optional runtime identifier"
        "output": "Optional output directory"
        "verbosity": "Optional dotnet verbosity level"
    """

    log_message = "Cleaning..."
    failure_label = "Clean"

    def _build_arguments(self, args: dict, base_path: Path) -> list[str]:
        command = ["clean"]
        self._append_common_options(command, args, base_path)
        return command
