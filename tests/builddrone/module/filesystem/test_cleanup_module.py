import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from builddrone.drone_exception import DroneException
from builddrone.module.filesystem.cleanup_module import CleanupModule
from builddrone.runner import Runner


class TestCleanupModule(unittest.TestCase):

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

        self.test_file = os.path.join(self.temp_dir, "test_file.txt")

        self.test_folder = os.path.join(self.temp_dir, "test_folder")

        os.makedirs(self.test_folder)

        with open(self.test_file, "w") as f:
            f.write("test content")

        self.mock_runner = MagicMock(spec=Runner)
        self.mock_runner.logger = MagicMock()

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_run_with_files_and_folders(self):
        cleanup = CleanupModule()

        args = {"files": [self.test_file], "folders": [self.test_folder]}

        cleanup.run(self.mock_runner, args)

        self.assertFalse(os.path.exists(self.test_file))
        self.assertFalse(os.path.exists(self.test_folder))

        self.mock_runner.logger.info.assert_any_call("Cleaning up...")

        self.mock_runner.logger.info.assert_any_call(f"Deleted file: {self.test_file}")

        self.mock_runner.logger.info.assert_any_call(
            f"Deleted folder: {self.test_folder}"
        )

    def test_run_with_nonexistent_files(self):
        cleanup = CleanupModule()

        nonexistent_file = "/nonexistent/file.txt"

        with self.assertRaises(DroneException) as context:
            cleanup.run(self.mock_runner, {"files": [nonexistent_file]})

        self.assertEqual(str(context.exception), f"Is not a file: {nonexistent_file}")
        self.mock_runner.logger.error.assert_not_called()

    def test_run_with_nonexistent_folders(self):
        cleanup = CleanupModule()

        nonexistent_folder = "/nonexistent/folder"

        with self.assertRaises(DroneException) as context:
            cleanup.run(self.mock_runner, {"folders": [nonexistent_folder]})

        self.assertEqual(
            str(context.exception), f"Is not a folder: {nonexistent_folder}"
        )
        self.mock_runner.logger.error.assert_not_called()

    def test_run_with_empty_args(self):
        cleanup = CleanupModule()

        cleanup.run(self.mock_runner, {})

        self.mock_runner.logger.info.assert_called_with("Cleaning up...")

    @patch("builddrone.module.filesystem.cleanup_module.os.remove")
    @patch("builddrone.module.filesystem.cleanup_module.os.path.isfile")
    def test_delete_files_with_exception(self, mock_isfile, mock_remove):
        mock_isfile.return_value = True
        mock_remove.side_effect = PermissionError("Permission denied")

        cleanup = CleanupModule()

        with self.assertRaises(DroneException) as context:
            cleanup._delete_files(self.mock_runner, ["/some/file.txt"])

        self.assertEqual(
            str(context.exception),
            "Error deleting file /some/file.txt : Permission denied",
        )
        self.mock_runner.logger.error.assert_called_with(
            "Error deleting file /some/file.txt : Permission denied"
        )

    @patch("builddrone.module.filesystem.cleanup_module.shutil.rmtree")
    @patch("builddrone.module.filesystem.cleanup_module.os.path.isdir")
    def test_delete_folders_with_exception(self, mock_isdir, mock_rmtree):
        mock_isdir.return_value = True
        mock_rmtree.side_effect = PermissionError("Permission denied")

        cleanup = CleanupModule()

        with self.assertRaises(DroneException) as context:
            cleanup._delete_folders(self.mock_runner, ["/some/folder"])

        self.assertEqual(
            str(context.exception),
            "Error deleting folder /some/folder : Permission denied",
        )
        self.mock_runner.logger.error.assert_called_with(
            "Error deleting folder /some/folder : Permission denied"
        )
