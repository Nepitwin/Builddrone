"""dotnet pack module."""

from __future__ import annotations

from pathlib import Path

from builddrone.module.dotnet.dotnet_base_module import DotnetBaseModule
from builddrone.module.dotnet.dotnet_projects import (
    package_paths,
    selected_project_files,
)
from builddrone.path_safety import reject_symlink_component


class DotnetPackModule(DotnetBaseModule):  # pylint: disable=too-few-public-methods
    """Build a NuGet package with ``dotnet pack``.

    Fails before ``dotnet pack`` runs when the output package is a symlink.
    That file is ``{PackageId}.{Version}.nupkg``. With ``include_symbols``,
    the ``.snupkg`` and ``.symbols.nupkg`` names are rejected as well.

    Blueprint configuration arguments:
        "project": "Optional project or solution path"
        "configuration": "Optional build configuration, such as Release"
        "output": "Optional directory for the generated package"
        "verbosity": "Optional dotnet verbosity level"
        "version_suffix": "Optional pre-release version suffix"
        "no_build": "Skip building before packing"
        "no_restore": "Skip restore before packing"
        "include_symbols": "Include a symbols package"
        "include_source": "Include sources in the symbols package"
    """

    log_message = "Packing..."
    failure_label = "Pack"

    def _build_arguments(self, args: dict, base_path: Path) -> list[str]:
        command = ["pack"]
        self._append_project(command, args, base_path)
        self._append_configuration(command, args)
        self._append_output(command, args, base_path)
        self._append_verbosity(command, args)
        version_suffix = self._optional_string(args, "version_suffix")
        if version_suffix is not None:
            command.extend(["--version-suffix", version_suffix])
        self._append_switch(command, args, "no_build", "--no-build")
        self._append_switch(command, args, "no_restore", "--no-restore")
        self._append_switch(command, args, "include_symbols", "--include-symbols")
        self._append_switch(command, args, "include_source", "--include-source")
        self._reject_package_symlinks(args, base_path, version_suffix)
        return command

    def _reject_package_symlinks(
        self, args: dict, base_path: Path, version_suffix: str | None
    ) -> None:
        """Reject symlinks at the nupkg and symbol package ``dotnet pack`` writes."""
        output = self._directory_argument(args, base_path, "output", "Output")
        output_directory = Path(output) if output is not None else None
        configuration = self._optional_string(args, "configuration") or "Debug"
        include_symbols = self._optional_bool(args, "include_symbols")
        projects = selected_project_files(
            self._project_path(args, base_path), base_path
        )
        for project in projects:
            for package in package_paths(
                project,
                output_directory,
                configuration,
                version_suffix,
                include_symbols,
            ):
                reject_symlink_component(package, base_path, "Package")
