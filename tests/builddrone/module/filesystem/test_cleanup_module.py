"""Tests for the filesystem cleanup module."""

# These tests share symlink setup patterns with other filesystem modules.
# pylint: disable=duplicate-code,too-many-public-methods

import os
import shutil
import tempfile
import unittest
from pathlib import Path
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

    def test_run_rejects_symlinked_file(self):
        """Reject a file path that is a symlink instead of deleting its target."""
        secret_file = os.path.join(self.temp_dir, "secret.txt")
        with open(secret_file, "w", encoding="utf-8") as file:
            file.write("secret-data")

        link_path = os.path.join(self.temp_dir, "linked.txt")
        try:
            os.symlink(secret_file, link_path)
        except OSError:
            self.skipTest("Cannot create symlinks on this platform")

        cleanup = CleanupModule()
        with self.assertRaises(DroneException) as context:
            cleanup.run(self.mock_runner, {"files": ["linked.txt"]})

        self.assertEqual(
            str(context.exception),
            f"Cleanup file must not be a symlink: {Path(link_path)}",
        )
        self.assertTrue(os.path.isfile(secret_file))
        self.assertTrue(os.path.islink(link_path))

    def test_run_rejects_symlinked_file_when_symlinks_unavailable(self):
        """Reject a file path reported as a symlink instead of deleting it."""
        link_path = Path(self.temp_dir) / "linked.txt"
        link_path.write_text("linked", encoding="utf-8")
        original_is_symlink = Path.is_symlink

        def fake_is_symlink(path_self):
            if path_self == link_path:
                return True
            return original_is_symlink(path_self)

        cleanup = CleanupModule()
        with patch.object(Path, "is_symlink", fake_is_symlink):
            with self.assertRaises(DroneException) as context:
                cleanup.run(self.mock_runner, {"files": ["linked.txt"]})

        self.assertEqual(
            str(context.exception),
            f"Cleanup file must not be a symlink: {link_path}",
        )
        self.assertTrue(link_path.is_file())

    def test_run_rejects_symlinked_folder(self):
        """Reject a folder symlink instead of deleting its target."""
        host_dir = os.path.join(self.temp_dir, "host")
        os.makedirs(host_dir)
        secret_file = os.path.join(host_dir, "job.env")
        with open(secret_file, "w", encoding="utf-8") as file:
            file.write("secret-data")

        link_path = os.path.join(self.temp_dir, "linked_dir")
        try:
            os.symlink(host_dir, link_path, target_is_directory=True)
        except OSError:
            self.skipTest("Cannot create directory symlinks on this platform")

        cleanup = CleanupModule()
        with self.assertRaises(DroneException) as context:
            cleanup.run(self.mock_runner, {"folders": ["linked_dir"]})

        self.assertEqual(
            str(context.exception),
            f"Cleanup folder must not be a symlink: {Path(link_path)}",
        )
        self.assertTrue(os.path.isdir(host_dir))
        self.assertTrue(os.path.isfile(secret_file))

    def test_run_rejects_symlinked_folder_when_symlinks_unavailable(self):
        """Reject a folder path reported as a directory symlink."""
        link_path = Path(self.temp_dir) / "linked_dir"
        link_path.mkdir()
        (link_path / "job.env").write_text("secret-data", encoding="utf-8")
        original_is_symlink = Path.is_symlink

        def fake_is_symlink(path_self):
            if path_self == link_path:
                return True
            return original_is_symlink(path_self)

        cleanup = CleanupModule()
        with patch.object(Path, "is_symlink", fake_is_symlink):
            with self.assertRaises(DroneException) as context:
                cleanup.run(self.mock_runner, {"folders": ["linked_dir"]})

        self.assertEqual(
            str(context.exception),
            f"Cleanup folder must not be a symlink: {link_path}",
        )
        self.assertTrue((link_path / "job.env").is_file())

    def test_run_rejects_intermediate_file_directory_symlink(self):
        """Reject a nested file whose prefix is a directory symlink."""
        host_dir = os.path.join(self.temp_dir, "host")
        os.makedirs(host_dir)
        secret_file = os.path.join(host_dir, "summary.txt")
        with open(secret_file, "w", encoding="utf-8") as file:
            file.write("secret-data")

        outer_link = os.path.join(self.temp_dir, "result")
        try:
            os.symlink(host_dir, outer_link, target_is_directory=True)
        except OSError:
            self.skipTest("Cannot create directory symlinks on this platform")

        cleanup = CleanupModule()
        with self.assertRaises(DroneException) as context:
            cleanup.run(self.mock_runner, {"files": ["result/summary.txt"]})

        self.assertEqual(
            str(context.exception),
            f"Cleanup file must not be a symlink: {Path(outer_link)}",
        )
        self.assertTrue(os.path.isfile(secret_file))

    def test_run_rejects_intermediate_file_directory_symlink_when_symlinks_unavailable(
        self,
    ):
        """Reject a nested file whose prefix is reported as a directory symlink."""
        outer_dir = Path(self.temp_dir) / "result"
        outer_dir.mkdir()
        (outer_dir / "summary.txt").write_text("secret-data", encoding="utf-8")
        original_is_symlink = Path.is_symlink

        def fake_is_symlink(path_self):
            if path_self == outer_dir:
                return True
            return original_is_symlink(path_self)

        cleanup = CleanupModule()
        with patch.object(Path, "is_symlink", fake_is_symlink):
            with self.assertRaises(DroneException) as context:
                cleanup.run(self.mock_runner, {"files": ["result/summary.txt"]})

        self.assertEqual(
            str(context.exception),
            f"Cleanup file must not be a symlink: {outer_dir}",
        )
        self.assertTrue((outer_dir / "summary.txt").is_file())

    def test_run_rejects_intermediate_folder_directory_symlink(self):
        """Reject a nested folder whose prefix is a directory symlink."""
        host_dir = os.path.join(self.temp_dir, "host")
        cache_dir = os.path.join(host_dir, "cache")
        os.makedirs(cache_dir)
        secret_file = os.path.join(cache_dir, "job.env")
        with open(secret_file, "w", encoding="utf-8") as file:
            file.write("secret-data")

        outer_link = os.path.join(self.temp_dir, "result")
        try:
            os.symlink(host_dir, outer_link, target_is_directory=True)
        except OSError:
            self.skipTest("Cannot create directory symlinks on this platform")

        cleanup = CleanupModule()
        with self.assertRaises(DroneException) as context:
            cleanup.run(self.mock_runner, {"folders": ["result/cache"]})

        self.assertEqual(
            str(context.exception),
            f"Cleanup folder must not be a symlink: {Path(outer_link)}",
        )
        self.assertTrue(os.path.isdir(cache_dir))
        self.assertTrue(os.path.isfile(secret_file))

    def test_run_rejects_intermediate_folder_directory_symlink_when_symlinks_unavailable(
        self,
    ):
        """Reject a nested folder whose prefix is reported as a directory symlink."""
        outer_dir = Path(self.temp_dir) / "result"
        cache_dir = outer_dir / "cache"
        cache_dir.mkdir(parents=True)
        (cache_dir / "job.env").write_text("secret-data", encoding="utf-8")
        original_is_symlink = Path.is_symlink

        def fake_is_symlink(path_self):
            if path_self == outer_dir:
                return True
            return original_is_symlink(path_self)

        cleanup = CleanupModule()
        with patch.object(Path, "is_symlink", fake_is_symlink):
            with self.assertRaises(DroneException) as context:
                cleanup.run(self.mock_runner, {"folders": ["result/cache"]})

        self.assertEqual(
            str(context.exception),
            f"Cleanup folder must not be a symlink: {outer_dir}",
        )
        self.assertTrue((cache_dir / "job.env").is_file())
