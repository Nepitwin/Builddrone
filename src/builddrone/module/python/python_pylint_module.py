"""Python linting module."""

from __future__ import annotations

import os
from pathlib import Path

from builddrone.base_module import BaseModule
from builddrone.drone_exception import DroneException
from builddrone.path_safety import reject_symlink_component
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

        base_path = Path(runner.get_base_path())
        ignore_names = set(ignore)
        for target in [*paths, *files]:
            self._reject_lint_target(target, base_path, ignore_names)

        command = ["-m", "pylint"]
        if ignore:
            command.extend(["--ignore", ",".join(ignore)])
        command.extend([*paths, *files])

        exit_code = runner.run(command, cwd=str(base_path))

        if exit_code != 0:
            raise DroneException(f"Pylint failed with exit code {exit_code}")

    def _reject_lint_target(
        self, target: str, base_path: Path, ignore_names: set[str]
    ) -> None:
        resolved = self._resolve_path(target, base_path)
        reject_symlink_component(resolved, base_path, "Pylint path")
        if resolved.is_dir():
            self._reject_walked_symlinks(resolved, base_path, ignore_names)

    @staticmethod
    def _resolve_path(path: str, base_path: Path) -> Path:
        resolved = Path(path)
        if not os.path.isabs(path):
            resolved = base_path / resolved
        return resolved

    @staticmethod
    def _reject_walked_symlinks(
        directory: Path, base_path: Path, ignore_names: set[str]
    ) -> None:
        for root, dir_names, file_names in os.walk(directory, followlinks=False):
            dir_names[:] = [name for name in dir_names if name not in ignore_names]
            for dir_name in dir_names:
                reject_symlink_component(
                    Path(root) / dir_name, base_path, "Pylint path"
                )
            for file_name in file_names:
                if file_name in ignore_names:
                    continue
                reject_symlink_component(
                    Path(root) / file_name, base_path, "Pylint path"
                )
