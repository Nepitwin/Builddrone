"""Filesystem cleanup module."""

import os
import shutil

from builddrone.base_module import BaseModule
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
        self._delete_files(runner, args.get("files", []))
        self._delete_folders(runner, args.get("folders", []))

    @staticmethod
    def _delete_files(runner: Runner, files: list):
        for file_path in files:
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    runner.logger.info(f"Deleted file: {file_path}")
            except OSError as e:
                runner.logger.error(f"Error deleting file {file_path}: {e}")

    @staticmethod
    def _delete_folders(runner: Runner, folders: list):
        for folder_path in folders:
            try:
                if os.path.isdir(folder_path):
                    shutil.rmtree(folder_path)
                    runner.logger.info(f"Deleted folder: {folder_path}")
            except OSError as e:
                runner.logger.error(f"Error deleting folder {folder_path}: {e}")
