"""dotnet restore module."""

from __future__ import annotations

from pathlib import Path

from builddrone.drone_exception import DroneException
from builddrone.module.dotnet.dotnet_base_module import DotnetBaseModule


class DotnetRestoreModule(DotnetBaseModule):  # pylint: disable=too-few-public-methods
    """Restore NuGet dependencies with ``dotnet restore``.

    Blueprint configuration arguments:
        "project": "Optional project or solution path"
        "sources": "Optional list of NuGet sources"
        "runtime": "Optional runtime identifier"
        "verbosity": "Optional dotnet verbosity level"
        "force": "Force restore when packages are already up to date"
    """

    log_message = "Restoring..."
    failure_label = "Restore"

    def _build_arguments(self, args: dict, base_path: Path) -> list[str]:
        command = ["restore"]
        self._append_project(command, args, base_path)
        self._append_sources(command, args)
        self._append_runtime(command, args)
        self._append_verbosity(command, args)
        self._append_switch(command, args, "force", "--force")
        return command

    @staticmethod
    def _append_sources(command: list[str], args: dict) -> None:
        """Append each configured NuGet source."""
        sources = args.get("sources", [])
        if not isinstance(sources, list):
            raise DroneException("Argument 'sources' must be a list")

        for source in sources:
            if not isinstance(source, str) or not source.strip():
                raise DroneException(
                    "Argument 'sources' must contain non-empty strings"
                )
            command.extend(["--source", source])
