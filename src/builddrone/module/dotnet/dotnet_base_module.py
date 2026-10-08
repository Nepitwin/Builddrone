"""Shared helpers for dotnet CLI modules."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from builddrone.base_module import BaseModule
from builddrone.drone_exception import DroneException
from builddrone.path_safety import reject_symlink_component
from builddrone.runner import Runner

_VERBOSITY_LEVELS = {
    "q",
    "quiet",
    "m",
    "minimal",
    "n",
    "normal",
    "d",
    "detailed",
    "diag",
    "diagnostic",
}


class DotnetBaseModule(BaseModule):  # pylint: disable=too-few-public-methods
    """Common argument handling and ``dotnet`` execution."""

    log_message = ""
    failure_label = ""

    def run(self, runner: Runner, args: dict) -> None:
        """Build a dotnet command from ``args`` and run it.

        Args:
            runner: Runner instance used to execute commands.
            args: Module configuration arguments.
        """
        runner.logger.info(self.log_message)
        base_path = Path(runner.get_base_path())
        arguments = self._build_arguments(args, base_path)
        self._execute(runner, arguments, base_path)

    def _build_arguments(self, args: dict, base_path: Path) -> list[str]:
        """Return the ``dotnet`` arguments for this module."""
        raise DroneException(
            f"{self.failure_label} does not build a single dotnet command"
        )

    def _execute(self, runner: Runner, arguments: list[str], base_path: Path) -> None:
        """Run ``dotnet`` and raise when the command fails."""
        exit_code = runner.run_command(
            [self._dotnet_executable(), *arguments],
            cwd=str(base_path),
        )
        if exit_code != 0:
            raise DroneException(
                f"{self.failure_label} failed with exit code {exit_code}"
            )

    @staticmethod
    def _dotnet_executable() -> str:
        """Return the ``dotnet`` executable, or raise when it is missing."""
        dotnet = shutil.which("dotnet")
        if not dotnet:
            raise DroneException("dotnet is not installed")
        return dotnet

    @staticmethod
    def _optional_string(args: dict, name: str) -> str | None:
        """Return a non-empty string argument, or None when it is omitted."""
        value = args.get(name)
        if value is None:
            return None
        if not isinstance(value, str) or not value.strip():
            raise DroneException(f"Argument '{name}' must be a non-empty string")
        return value

    @staticmethod
    def _optional_bool(args: dict, name: str, default: bool = False) -> bool:
        """Return a boolean argument, using ``default`` when it is omitted."""
        value = args.get(name, default)
        if not isinstance(value, bool):
            raise DroneException(f"Argument '{name}' must be a boolean")
        return value

    @staticmethod
    def _resolve_path(path: str, base_path: Path) -> Path:
        """Resolve a relative path from the blueprint directory."""
        resolved = Path(path)
        if not os.path.isabs(path):
            resolved = base_path / resolved
        return resolved

    def _project_path(self, args: dict, base_path: Path) -> str | None:
        """Return an existing project or solution path."""
        project = self._optional_string(args, "project")
        if project is None:
            return None

        resolved = self._resolve_path(project, base_path)
        reject_symlink_component(resolved, base_path, "Project")
        if not resolved.exists():
            raise DroneException(f"Project not found: {resolved}")
        return str(resolved)

    def _directory_argument(
        self, args: dict, base_path: Path, name: str, kind: str
    ) -> str | None:
        """Return a directory path, creating nothing if it does not exist yet."""
        directory = self._optional_string(args, name)
        if directory is None:
            return None

        resolved = self._resolve_path(directory, base_path)
        reject_symlink_component(resolved, base_path, kind)
        if resolved.exists() and not resolved.is_dir():
            raise DroneException(f"{kind} must be a directory: {resolved}")
        return str(resolved)

    def _append_common_options(
        self, command: list[str], args: dict, base_path: Path
    ) -> None:
        """Append the options shared by clean and build."""
        self._append_project(command, args, base_path)
        self._append_configuration(command, args)
        self._append_framework(command, args)
        self._append_runtime(command, args)
        self._append_output(command, args, base_path)
        self._append_verbosity(command, args)

    def _append_project(self, command: list[str], args: dict, base_path: Path) -> None:
        """Append the project path when one is configured."""
        project = self._project_path(args, base_path)
        if project is not None:
            command.append(project)

    def _append_configuration(self, command: list[str], args: dict) -> None:
        """Append ``--configuration`` when one is configured."""
        configuration = self._optional_string(args, "configuration")
        if configuration is not None:
            command.extend(["--configuration", configuration])

    def _append_framework(self, command: list[str], args: dict) -> None:
        """Append ``--framework`` when a target framework is configured."""
        framework = self._optional_string(args, "framework")
        if framework is not None:
            command.extend(["--framework", framework])

    def _append_runtime(self, command: list[str], args: dict) -> None:
        """Append ``--runtime`` when one is configured."""
        runtime = self._optional_string(args, "runtime")
        if runtime is not None:
            command.extend(["--runtime", runtime])

    def _append_verbosity(self, command: list[str], args: dict) -> None:
        """Append ``--verbosity`` when a known level is configured."""
        verbosity = self._optional_string(args, "verbosity")
        if verbosity is None:
            return
        if verbosity not in _VERBOSITY_LEVELS:
            raise DroneException(
                "Argument 'verbosity' must be one of: "
                "q, m, n, d, diag, quiet, minimal, normal, detailed, diagnostic"
            )
        command.extend(["--verbosity", verbosity])

    def _append_output(self, command: list[str], args: dict, base_path: Path) -> None:
        """Append ``--output`` when an output directory is configured."""
        output = self._directory_argument(args, base_path, "output", "Output")
        if output is not None:
            command.extend(["--output", output])

    def _append_switch(
        self, command: list[str], args: dict, name: str, flag: str
    ) -> None:
        """Append a boolean switch when the argument is true."""
        if self._optional_bool(args, name):
            command.append(flag)
