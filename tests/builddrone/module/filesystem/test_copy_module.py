"""Tests for the filesystem copy module."""

import os
import shutil
import tempfile
import unittest
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
