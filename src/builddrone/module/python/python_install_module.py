"""Python install module."""

from __future__ import annotations

import os
from pathlib import Path

from builddrone.base_module import BaseModule
from builddrone.drone_exception import DroneException
from builddrone.path_safety import reject_symlink_component
from builddrone.runner import Runner


class PythonInstallModule(BaseModule):  # pylint: disable=too-few-public-methods
    """A module responsible for installing Python packages.

    Blueprint configuration arguments:
        "source": "Package source to install"
        "requirements": "Requirements file to install"
    """

    def run(self, runner: Runner, args: dict) -> None:
        """Install a package source with ``python -m pip install``.

        ``--disable-pip-version-check`` suppresses pip upgrade notices that
        otherwise go to stderr and fail PowerShell/AppVeyor hosts.

        Args:
            runner: Runner instance used to execute commands.
            args: Module configuration arguments.
        """
        runner.logger.info("Installing...")
        source = args.get("source")
        requirements = args.get("requirements")
        base_path = Path(runner.get_base_path())

        if isinstance(requirements, str) and requirements:
            requirements_path = self._resolve_path(requirements, base_path)
            reject_symlink_component(requirements_path, base_path, "Requirements file")
            install_args = ["-r", requirements]
        elif isinstance(source, str) and source:
            source_path = self._resolve_path(source, base_path)
            reject_symlink_component(source_path, base_path, "Install source")
            install_args = [source]
        else:
            raise DroneException("No source or requirements provided for install")

        exit_code = runner.run(
            ["-m", "pip", "install", "--disable-pip-version-check", *install_args],
            cwd=str(base_path),
        )

        if exit_code != 0:
            raise DroneException(f"Install failed with exit code {exit_code}")

    @staticmethod
    def _resolve_path(path: str, base_path: Path) -> Path:
        resolved = Path(path)
        if not os.path.isabs(path):
            resolved = base_path / resolved
        return resolved
