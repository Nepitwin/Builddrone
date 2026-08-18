"""Tests for the filesystem copy module."""

# These tests share symlink setup patterns with the archiver module tests.
# pylint: disable=duplicate-code

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from builddrone.drone_exception import DroneException
from builddrone.module.filesystem.copy_module import FilesystemCopyModule
from builddrone.runner import Runner


class TestFilesystemCopyModule(unittest.TestCase):
    """Verify copy behavior and error handling."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.mock_runner = MagicMock(spec=Runner)
        self.mock_runner.logger = MagicMock()
        self.mock_runner.get_base_path.return_value = self.temp_dir

        self.source_dir = os.path.join(self.temp_dir, "source")
        self.destination_dir = os.path.join(self.temp_dir, "destination")
        self.nested_dir = os.path.join(self.source_dir, "nested")

        os.makedirs(self.nested_dir)

        self.source_file = os.path.join(self.source_dir, "root.txt")
        self.nested_file = os.path.join(self.nested_dir, "nested.txt")
        image_file = os.path.join(self.source_dir, "root.jpg")
        nested_image_file = os.path.join(self.nested_dir, "nested.jpg")

        for file_path in (
            self.source_file,
            self.nested_file,
            image_file,
            nested_image_file,
        ):
            with open(file_path, "w", encoding="utf-8") as file:
                file.write(file_path)

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_run_copies_all_files_recursively(self):
        """Copy all files from absolute source to absolute destination."""
        module = FilesystemCopyModule()

        module.run(
            self.mock_runner,
            {
                "source": self.source_dir,
                "destination": self.destination_dir,
            },
        )

        self.assertTrue(os.path.isfile(os.path.join(self.destination_dir, "root.txt")))
        self.assertTrue(
            os.path.isfile(os.path.join(self.destination_dir, "nested", "nested.txt"))
        )
        self.mock_runner.logger.info.assert_any_call("Copying files...")

    def test_run_copies_only_files_matching_pattern(self):
        """Copy matching files at every level of the source tree."""
        module = FilesystemCopyModule()

        module.run(
            self.mock_runner,
            {
                "source": self.source_dir,
                "files": "*.jpg",
                "destination": self.destination_dir,
            },
        )

        self.assertTrue(os.path.isfile(os.path.join(self.destination_dir, "root.jpg")))
        self.assertTrue(
            os.path.isfile(os.path.join(self.destination_dir, "nested", "nested.jpg"))
        )
        self.assertFalse(os.path.exists(os.path.join(self.destination_dir, "root.txt")))
        self.assertFalse(
            os.path.exists(os.path.join(self.destination_dir, "nested", "nested.txt"))
        )

    def test_run_with_invalid_files_pattern_raises(self):
        """Reject a files filter that is not a non-empty string."""
        module = FilesystemCopyModule()

        with self.assertRaises(DroneException) as context:
            module.run(
                self.mock_runner,
                {
                    "source": self.source_dir,
                    "files": ["*.jpg"],
                    "destination": self.destination_dir,
                },
            )

        self.assertEqual(str(context.exception), "Invalid files pattern for copy")

    def test_run_resolves_relative_paths_from_blueprint_directory(self):
        """Resolve source and destination relative to the blueprint directory."""
        module = FilesystemCopyModule()

        module.run(
            self.mock_runner,
            {
                "source": "source",
                "destination": "destination",
            },
        )

        self.assertTrue(os.path.isfile(os.path.join(self.destination_dir, "root.txt")))
        self.assertTrue(
            os.path.isfile(os.path.join(self.destination_dir, "nested", "nested.txt"))
        )

    def test_run_without_source_raises(self):
        """Reject a missing source directory."""
        module = FilesystemCopyModule()

        with self.assertRaises(DroneException) as context:
            module.run(self.mock_runner, {"destination": self.destination_dir})

        self.assertEqual(str(context.exception), "No source provided for copy")

    def test_run_without_destination_raises(self):
        """Reject a missing destination directory."""
        module = FilesystemCopyModule()

        with self.assertRaises(DroneException) as context:
            module.run(self.mock_runner, {"source": self.source_dir})

        self.assertEqual(str(context.exception), "No destination provided for copy")

    def test_run_with_non_directory_source_raises(self):
        """Reject a source that is not a directory."""
        module = FilesystemCopyModule()

        with self.assertRaises(DroneException) as context:
            module.run(
                self.mock_runner,
                {"source": self.source_file, "destination": self.destination_dir},
            )

        self.assertEqual(
            str(context.exception),
            f"Source is not a directory: {self.source_file}",
        )

    @patch("builddrone.module.filesystem.copy_module.shutil.copy2")
    @patch("builddrone.module.filesystem.copy_module.os.makedirs")
    def test_run_with_copy_exception(self, _mock_makedirs, mock_copy2):
        """Surface copy failures through DroneException."""
        mock_copy2.side_effect = PermissionError("Permission denied")

        module = FilesystemCopyModule()

        with self.assertRaises(DroneException) as context:
            module.run(
                self.mock_runner,
                {
                    "source": self.source_dir,
                    "destination": self.destination_dir,
                },
            )

        attempted_source = mock_copy2.call_args.args[0]
        self.assertEqual(
            str(context.exception),
            f"Error copying file {attempted_source} : Permission denied",
        )
        self.mock_runner.logger.error.assert_called_with(
            f"Error copying file {attempted_source} : Permission denied"
        )

    def test_run_skips_symlinked_file_when_symlinks_unavailable(self):
        """Skip files reported as symlinks instead of copying their targets."""
        link_path = Path(self.source_dir) / "linked.txt"
        link_path.write_text("linked", encoding="utf-8")
        original_is_symlink = Path.is_symlink

        def fake_is_symlink(path_self):
            if path_self == link_path:
                return True
            return original_is_symlink(path_self)

        module = FilesystemCopyModule()
        with patch.object(Path, "is_symlink", fake_is_symlink):
            module.run(
                self.mock_runner,
                {
                    "source": self.source_dir,
                    "destination": self.destination_dir,
                },
            )

        self.assertTrue(os.path.isfile(os.path.join(self.destination_dir, "root.txt")))
        self.assertFalse(
            os.path.exists(os.path.join(self.destination_dir, "linked.txt"))
        )
        self.mock_runner.logger.warning.assert_called_once_with(
            "Skipping symlink: %s",
            link_path,
        )

    def test_run_skips_symlinked_file(self):
        """Skip symlinked files instead of copying their targets."""
        secret_file = os.path.join(self.temp_dir, "secret.txt")
        with open(secret_file, "w", encoding="utf-8") as file:
            file.write("secret-data")

        link_path = os.path.join(self.source_dir, "linked.txt")
        try:
            os.symlink(secret_file, link_path)
        except OSError:
            self.skipTest("Cannot create symlinks on this platform")

        module = FilesystemCopyModule()
        module.run(
            self.mock_runner,
            {
                "source": self.source_dir,
                "destination": self.destination_dir,
            },
        )

        destination_link = os.path.join(self.destination_dir, "linked.txt")
        self.assertFalse(os.path.exists(destination_link))
        self.mock_runner.logger.warning.assert_called_once_with(
            "Skipping symlink: %s",
            Path(link_path),
        )

    def test_run_skips_symlinked_files_in_folder(self):
        """Skip symlinked files encountered while copying folders."""
        secret_file = os.path.join(self.temp_dir, "secret.txt")
        with open(secret_file, "w", encoding="utf-8") as file:
            file.write("secret-data")

        link_path = os.path.join(self.nested_dir, "linked.txt")
        try:
            os.symlink(secret_file, link_path)
        except OSError:
            self.skipTest("Cannot create symlinks on this platform")

        module = FilesystemCopyModule()
        module.run(
            self.mock_runner,
            {
                "source": self.source_dir,
                "destination": self.destination_dir,
            },
        )

        self.assertTrue(os.path.isfile(os.path.join(self.destination_dir, "root.txt")))
        self.assertFalse(
            os.path.exists(os.path.join(self.destination_dir, "nested", "linked.txt"))
        )
        self.mock_runner.logger.warning.assert_called_once_with(
            "Skipping symlink: %s",
            Path(link_path),
        )

    def test_run_rejects_symlinked_source(self):
        """Reject a source path that is a directory symlink."""
        host_dir = os.path.join(self.temp_dir, "host")
        os.makedirs(host_dir)
        secret_file = os.path.join(host_dir, "job.env")
        with open(secret_file, "w", encoding="utf-8") as file:
            file.write("secret-data")

        shutil.rmtree(self.source_dir)
        try:
            os.symlink(host_dir, self.source_dir, target_is_directory=True)
        except OSError:
            self.skipTest("Cannot create directory symlinks on this platform")

        module = FilesystemCopyModule()
        with self.assertRaises(DroneException) as context:
            module.run(
                self.mock_runner,
                {
                    "source": self.source_dir,
                    "destination": self.destination_dir,
                },
            )

        self.assertEqual(
            str(context.exception),
            f"Source must not be a symlink: {Path(self.source_dir)}",
        )
        self.assertFalse(os.path.exists(os.path.join(self.destination_dir, "job.env")))

    def test_run_rejects_symlinked_source_when_symlinks_unavailable(self):
        """Reject a source path reported as a directory symlink."""
        original_is_symlink = Path.is_symlink
        source_path = Path(self.source_dir)

        def fake_is_symlink(path_self):
            if path_self == source_path:
                return True
            return original_is_symlink(path_self)

        module = FilesystemCopyModule()
        with patch.object(Path, "is_symlink", fake_is_symlink):
            with self.assertRaises(DroneException) as context:
                module.run(
                    self.mock_runner,
                    {
                        "source": self.source_dir,
                        "destination": self.destination_dir,
                    },
                )

        self.assertEqual(
            str(context.exception),
            f"Source must not be a symlink: {source_path}",
        )

    def test_run_skips_nested_symlinked_directory(self):
        """Do not traverse nested directory symlinks while copying folders."""
        host_dir = os.path.join(self.temp_dir, "host")
        os.makedirs(host_dir)
        secret_file = os.path.join(host_dir, "job.env")
        with open(secret_file, "w", encoding="utf-8") as file:
            file.write("secret-data")

        link_path = os.path.join(self.source_dir, "linked_dir")
        try:
            os.symlink(host_dir, link_path, target_is_directory=True)
        except OSError:
            self.skipTest("Cannot create directory symlinks on this platform")

        module = FilesystemCopyModule()
        module.run(
            self.mock_runner,
            {
                "source": self.source_dir,
                "destination": self.destination_dir,
            },
        )

        self.assertTrue(os.path.isfile(os.path.join(self.destination_dir, "root.txt")))
        self.assertFalse(
            os.path.exists(os.path.join(self.destination_dir, "linked_dir", "job.env"))
        )
