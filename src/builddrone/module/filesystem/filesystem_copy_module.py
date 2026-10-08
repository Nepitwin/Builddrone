"""Filesystem copy module."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from builddrone.base_module import BaseModule
from builddrone.drone_exception import DroneException
from builddrone.path_safety import reject_symlink_component
from builddrone.runner import Runner


class FilesystemCopyModule(BaseModule):  # pylint: disable=too-few-public-methods
    """A module responsible for copying files from one folder to another.

    Blueprint configuration arguments:
        "source": "Source directory to copy from"
        "files": "Optional glob pattern selecting files to copy"
        "destination": "Destination directory to copy to"
    """

    def run(self, runner: Runner, args: dict) -> None:
        """Copy all files from a source directory into a destination directory."""
        runner.logger.info("Copying files...")
        source = args.get("source")
        destination = args.get("destination")
        base_path = Path(runner.get_base_path())

        if not isinstance(source, str) or not source:
            raise DroneException("No source provided for copy")

        if not isinstance(destination, str) or not destination:
            raise DroneException("No destination provided for copy")

        if args.get("files") is not None and (
            not isinstance(args.get("files"), str) or not args.get("files")
        ):
            raise DroneException("Invalid files pattern for copy")

        self._copy_tree(runner, source, destination, base_path, args.get("files"))

    @staticmethod
    def _copy_tree(
        runner: Runner,
        source: str,
        destination: str,
        base_path: Path,
        files_pattern: str | None = None,
    ) -> None:
        """Copy matching files from a directory tree preserving relative paths."""
        source_path = Path(source)
        destination_path = Path(destination)

        if not os.path.isabs(source):
            source_path = base_path / source_path

        if not os.path.isabs(destination):
            destination_path = base_path / destination_path

        reject_symlink_component(source_path, base_path, "Source")
        if not os.path.isdir(source_path):
            raise DroneException(f"Source is not a directory: {source_path}")

        reject_symlink_component(destination_path, base_path, "Destination")
        os.makedirs(destination_path, exist_ok=True)

        for root, _, files in os.walk(source_path, followlinks=False):
            relative_root = os.path.relpath(root, source_path)
            target_root = (
                destination_path
                if relative_root == "."
                else destination_path / relative_root
            )
            reject_symlink_component(target_root, base_path, "Destination")
            os.makedirs(target_root, exist_ok=True)

            for file_name in files:
                if files_pattern and not Path(relative_root, file_name).match(
                    files_pattern
                ):
                    continue

                source_file = Path(root) / file_name
                if source_file.is_symlink():
                    runner.logger.warning("Skipping symlink: %s", source_file)
                    continue

                destination_file = Path(target_root) / file_name
                reject_symlink_component(destination_file, base_path, "Destination")
                FilesystemCopyModule._copy_file(
                    runner, str(source_file), str(destination_file)
                )

    @staticmethod
    def _copy_file(runner: Runner, source_file: str, destination_file: str) -> None:
        """Copy one file and expose filesystem failures as module errors."""
        try:
            shutil.copy2(source_file, destination_file)
            runner.logger.info("Copied file: %s", source_file)
        except OSError as exc:
            msg = f"Error copying file {source_file} : {exc}"
            runner.logger.error(msg)
            raise DroneException(msg) from exc
