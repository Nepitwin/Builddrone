"""dotnet build module."""

from __future__ import annotations

from pathlib import Path

from builddrone.module.dotnet.dotnet_base_module import DotnetBaseModule


class DotnetBuildModule(DotnetBaseModule):  # pylint: disable=too-few-public-methods
    """Build a .NET project or solution with ``dotnet build``.

    Blueprint configuration arguments:
        "project": "Optional project or solution path"
        "configuration": "Optional build configuration, such as Release"
        "framework": "Optional target framework, such as net10.0"
        "runtime": "Optional runtime identifier"
        "output": "Optional output directory"
        "verbosity": "Optional dotnet verbosity level"
        "no_restore": "Skip restore before building"
    """

    log_message = "Building..."
    failure_label = "Build"

    def _build_arguments(self, args: dict, base_path: Path) -> list[str]:
        command = ["build"]
        self._append_common_options(command, args, base_path)
        self._append_switch(command, args, "no_restore", "--no-restore")
        return command
