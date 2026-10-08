"""dotnet pack module."""

from __future__ import annotations

from pathlib import Path

from builddrone.module.dotnet.dotnet_base_module import DotnetBaseModule


class DotnetPackModule(DotnetBaseModule):  # pylint: disable=too-few-public-methods
    """Build a NuGet package with ``dotnet pack``.

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
        return command
