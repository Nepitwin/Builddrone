"""Filesystem copy module."""

import os
import shutil

from builddrone.base_module import BaseModule
from builddrone.drone_exception import DroneException
from builddrone.runner import Runner


class FilesystemCopyModule(BaseModule):  # pylint: disable=too-few-public-methods
    """A module responsible for copying files from one folder to another.

    Blueprint configuration arguments:
        "source": "Source directory to copy from"
        "destination": "Destination directory to copy to"
    """

    def run(self, runner: Runner, args: dict) -> None:
        """Copy all files from a source directory into a destination directory."""
        runner.logger.info("Copying files...")
        source = args.get("source")
        destination = args.get("destination")

        if not isinstance(source, str) or not source:
            raise DroneException("No source provided for copy")

        if not isinstance(destination, str) or not destination:
            raise DroneException("No destination provided for copy")

        self._copy_tree(runner, source, destination)

    @staticmethod
    def _copy_tree(runner: Runner, source: str, destination: str) -> None:
        """Copy a directory tree preserving relative paths."""
        if not os.path.isdir(source):
            raise DroneException(f"Source is not a directory: {source}")

        os.makedirs(destination, exist_ok=True)

        for root, _, files in os.walk(source):
            relative_root = os.path.relpath(root, source)
            target_root = (
                destination
                if relative_root == "."
                else os.path.join(destination, relative_root)
            )
            os.makedirs(target_root, exist_ok=True)

            for file_name in files:
                source_file = os.path.join(root, file_name)
                destination_file = os.path.join(target_root, file_name)
                try:
                    shutil.copy2(source_file, destination_file)
                    runner.logger.info("Copied file: %s", source_file)
                except OSError as exc:
                    msg = f"Error copying file {source_file} : {exc}"
                    runner.logger.error(msg)
                    raise DroneException(msg) from exc
