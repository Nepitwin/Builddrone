"""Tests for the filesystem cleanup module."""

import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from builddrone.drone_exception import DroneException
from builddrone.module.filesystem.cleanup_module import CleanupModule
from builddrone.runner import Runner


class TestCleanupModule(unittest.TestCase):
    """Verify cleanup behavior and error handling."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

        self.test_file = os.path.join(self.temp_dir, "test_file.txt")
        self.relative_file = "test_file.txt"

        self.test_folder = os.path.join(self.temp_dir, "test_folder")
        self.relative_folder = "test_folder"

        os.makedirs(self.test_folder)

        with open(self.test_file, "w", encoding="utf-8") as file:
            file.write("test content")

        self.mock_runner = MagicMock(spec=Runner)
        self.mock_runner.logger = MagicMock()
        self.mock_runner.get_base_path.return_value = self.temp_dir

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_run_with_files_and_folders(self):
        """Delete both a file and a folder successfully."""
        cleanup = CleanupModule()

        args = {
            "files": [self.relative_file],
            "folders": [self.relative_folder],
        }

        cleanup.run(self.mock_runner, args)

        self.assertFalse(os.path.exists(self.test_file))
        self.assertFalse(os.path.exists(self.test_folder))

        self.mock_runner.logger.info.assert_any_call("Cleaning up...")
        self.mock_runner.logger.info.assert_any_call(f"Deleted file: {self.test_file}")
        self.mock_runner.logger.info.assert_any_call(
            f"Deleted folder: {self.test_folder}"
        )

    def test_run_with_nonexistent_files(self):
        """Ignore missing files without raising."""
        cleanup = CleanupModule()

        cleanup.run(self.mock_runner, {"files": ["missing.txt"]})

        self.mock_runner.logger.error.assert_not_called()
        self.mock_runner.logger.info.assert_called_with("Cleaning up...")

    def test_run_with_nonexistent_folders(self):
        """Ignore missing folders without raising."""
        cleanup = CleanupModule()

        cleanup.run(self.mock_runner, {"folders": ["missing-folder"]})

        self.mock_runner.logger.error.assert_not_called()
        self.mock_runner.logger.info.assert_called_with("Cleaning up...")

    def test_run_with_empty_args(self):
        """Allow empty args without raising."""
        cleanup = CleanupModule()

        cleanup.run(self.mock_runner, {})

        self.mock_runner.logger.info.assert_called_with("Cleaning up...")

    @patch("builddrone.module.filesystem.cleanup_module.os.remove")
    def test_delete_files_with_exception(self, mock_remove):
        """Surface file-deletion failures through DroneException."""
        mock_remove.side_effect = PermissionError("Permission denied")

        cleanup = CleanupModule()

        with self.assertRaises(DroneException) as context:
            cleanup.run(self.mock_runner, {"files": [self.test_file]})

        self.assertEqual(
            str(context.exception),
            f"Error deleting file {self.test_file} : Permission denied",
        )
        self.mock_runner.logger.error.assert_called_with(
            f"Error deleting file {self.test_file} : Permission denied"
        )

    @patch("builddrone.module.filesystem.cleanup_module.shutil.rmtree")
    def test_delete_folders_with_exception(self, mock_rmtree):
        """Surface folder-deletion failures through DroneException."""
        mock_rmtree.side_effect = PermissionError("Permission denied")

        cleanup = CleanupModule()

        with self.assertRaises(DroneException) as context:
            cleanup.run(self.mock_runner, {"folders": [self.test_folder]})

        self.assertEqual(
            str(context.exception),
            f"Error deleting folder {self.test_folder} : Permission denied",
        )
        self.mock_runner.logger.error.assert_called_with(
            f"Error deleting folder {self.test_folder} : Permission denied"
        )
