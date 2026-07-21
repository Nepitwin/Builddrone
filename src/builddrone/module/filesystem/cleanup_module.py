"""Filesystem cleanup module."""

import os
import shutil
from pathlib import Path

from builddrone.base_module import BaseModule
from builddrone.drone_exception import DroneException
from builddrone.runner import Runner


class CleanupModule(BaseModule):  # pylint: disable=too-few-public-methods
    """A module responsible for cleanup operations.

    This module handles cleanup, such as removing temporary files or folders.

    Blueprint configuration arguments:
        "files": ["List of files to delete"]
        "folders": ["List of folders to delete"]
    """

    def run(self, runner: Runner, args: dict) -> None:
        runner.logger.info("Cleaning up...")
        base_path = Path(runner.get_base_path())
        self._delete_files(runner, args.get("files", []), base_path)
        self._delete_folders(runner, args.get("folders", []), base_path)

    @staticmethod
    def _delete_files(runner: Runner, files: list, base_path: Path):
        for file in files:
            resolved_file = Path(file)
            if not os.path.isabs(file):
                resolved_file = base_path / file

            if not os.path.exists(resolved_file):
                # If file not exists, nothing to delete
                continue

            try:
                if os.path.isfile(resolved_file):
                    os.remove(resolved_file)
                    runner.logger.info(f"Deleted file: {resolved_file}")
                else:
                    raise DroneException(f"Is not a file: {resolved_file}")
            except OSError as e:
                msg = f"Error deleting file {resolved_file} : {e}"
                runner.logger.error(msg)
                raise DroneException(msg) from e

    @staticmethod
    def _delete_folders(runner: Runner, folders: list, base_path: Path):
        for folder in folders:
            resolved_folder = Path(folder)
            if not os.path.isabs(folder):
                resolved_folder = base_path / folder

            if not os.path.exists(resolved_folder):
                # If folder not exists, nothing to delete
                continue

            try:
                if os.path.isdir(resolved_folder):
                    shutil.rmtree(resolved_folder)
                    runner.logger.info(f"Deleted folder: {resolved_folder}")
                else:
                    raise DroneException(f"Is not a folder: {resolved_folder}")
            except OSError as e:
                msg = f"Error deleting folder {resolved_folder} : {e}"
                runner.logger.error(msg)
                raise DroneException(msg) from e
