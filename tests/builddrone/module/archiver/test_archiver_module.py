"""Tests for the archiver module."""

import os
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from builddrone.drone_exception import DroneException
from builddrone.module.archiver.archiver_module import ArchiverModule
from builddrone.runner import Runner


class TestArchiverModule(unittest.TestCase):
    """Verify archive creation, validation, and path handling."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.mock_runner = MagicMock(spec=Runner)
        self.mock_runner.logger = MagicMock()
        self.mock_runner.get_base_path.return_value = self.temp_dir
        self.module = ArchiverModule()

        self.result_dir = os.path.join(self.temp_dir, "result")
        self.nested_dir = os.path.join(self.result_dir, "nested")
        os.makedirs(self.nested_dir)

        self.root_file = os.path.join(self.result_dir, "root.txt")
        self.nested_file = os.path.join(self.nested_dir, "nested.txt")
        for file_path in (self.root_file, self.nested_file):
            with open(file_path, "w", encoding="utf-8") as file:
                file.write(file_path)

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_run_archives_folder(self):
        """Archive a folder preserving its top-level directory name."""
        archive_path = os.path.join(self.temp_dir, "results.zip")

        self.module.run(
            self.mock_runner,
            {"filename": "results.zip", "folders": ["result"]},
        )

        self.assertTrue(os.path.isfile(archive_path))
        with zipfile.ZipFile(archive_path) as archive:
            names = sorted(archive.namelist())
            self.assertEqual(
                names,
                ["result/nested/nested.txt", "result/root.txt"],
            )

    def test_run_archives_single_file(self):
        """Archive an individual file using its configured path."""
        archive_path = os.path.join(self.temp_dir, "results.zip")

        self.module.run(
            self.mock_runner,
            {
                "filename": "results.zip",
                "files": ["result/root.txt"],
            },
        )

        with zipfile.ZipFile(archive_path) as archive:
            self.assertEqual(archive.namelist(), ["result/root.txt"])
            self.assertEqual(
                archive.read("result/root.txt").decode("utf-8"),
                self.root_file,
            )

    def test_run_archives_folders_and_files_together(self):
        """Archive both folders and individual files into one zip."""
        extra_file = os.path.join(self.temp_dir, "extra.txt")
        with open(extra_file, "w", encoding="utf-8") as file:
            file.write("extra")

        self.module.run(
            self.mock_runner,
            {
                "filename": "results.zip",
                "folders": ["result"],
                "files": ["extra.txt"],
            },
        )

        with zipfile.ZipFile(os.path.join(self.temp_dir, "results.zip")) as archive:
            self.assertEqual(
                sorted(archive.namelist()),
                ["extra.txt", "result/nested/nested.txt", "result/root.txt"],
            )

    def test_run_overwrites_existing_archive(self):
        """Replace an existing archive when filename already exists."""
        archive_path = Path(self.temp_dir) / "results.zip"
        archive_path.write_text("old", encoding="utf-8")

        self.module.run(
            self.mock_runner,
            {"filename": "results.zip", "files": ["result/root.txt"]},
        )

        with zipfile.ZipFile(archive_path) as archive:
            self.assertEqual(archive.namelist(), ["result/root.txt"])

    def test_run_creates_parent_directories(self):
        """Create parent directories for the destination archive."""
        self.module.run(
            self.mock_runner,
            {
                "filename": "output/archives/results.zip",
                "files": ["result/root.txt"],
            },
        )

        self.assertTrue(
            os.path.isfile(
                os.path.join(self.temp_dir, "output", "archives", "results.zip")
            )
        )

    def test_run_requires_filename(self):
        """Reject a missing or blank filename."""
        with self.assertRaises(DroneException) as context:
            self.module.run(self.mock_runner, {"folders": ["result"]})

        self.assertEqual(
            str(context.exception),
            "Argument 'filename' must be a non-empty string",
        )

    def test_run_requires_folders_or_files(self):
        """Reject archives with no folders or files configured."""
        with self.assertRaises(DroneException) as context:
            self.module.run(self.mock_runner, {"filename": "results.zip"})

        self.assertEqual(
            str(context.exception),
            "At least one of 'folders' or 'files' must be a non-empty list",
        )

    def test_run_rejects_invalid_folder_entries(self):
        """Reject blank folder entries."""
        with self.assertRaises(DroneException) as context:
            self.module.run(
                self.mock_runner,
                {"filename": "results.zip", "folders": ["result", ""]},
            )

        self.assertEqual(
            str(context.exception),
            "Argument 'folders' must contain non-empty strings",
        )

    def test_run_rejects_missing_folder(self):
        """Fail when a configured folder does not exist."""
        with self.assertRaises(DroneException) as context:
            self.module.run(
                self.mock_runner,
                {"filename": "results.zip", "folders": ["missing"]},
            )

        self.assertEqual(
            str(context.exception),
            f"Folder not found: {Path(self.temp_dir) / 'missing'}",
        )

    @patch(
        "builddrone.module.archiver.archiver_module.Path.is_symlink",
        return_value=True,
    )
    def test_run_skips_symlinked_file_when_symlinks_unavailable(self, _mock_is_symlink):
        """Skip symlinked files instead of packing their targets."""
        archive_path = os.path.join(self.temp_dir, "results.zip")
        self.module.run(
            self.mock_runner,
            {"filename": "results.zip", "files": ["result/root.txt"]},
        )

        with zipfile.ZipFile(archive_path) as archive:
            self.assertEqual(archive.namelist(), [])

        self.mock_runner.logger.warning.assert_called_once()

    def test_run_skips_symlinked_files_in_folder_when_symlinks_unavailable(self):
        """Skip symlinked files encountered while archiving folders."""
        link_path = Path(self.result_dir) / "linked.txt"
        link_path.write_text("linked", encoding="utf-8")
        original_is_symlink = Path.is_symlink

        def fake_is_symlink(path_self):
            if path_self == link_path:
                return True
            return original_is_symlink(path_self)

        with patch.object(Path, "is_symlink", fake_is_symlink):
            self.module.run(
                self.mock_runner,
                {"filename": "results.zip", "folders": ["result"]},
            )

        with zipfile.ZipFile(os.path.join(self.temp_dir, "results.zip")) as archive:
            self.assertEqual(
                sorted(archive.namelist()),
                ["result/nested/nested.txt", "result/root.txt"],
            )

        self.mock_runner.logger.warning.assert_called_once_with(
            "Skipping symlink: %s",
            link_path,
        )

    def test_run_skips_symlinked_file(self):
        """Skip symlinked files instead of packing their targets."""
        secret_file = os.path.join(self.temp_dir, "secret.txt")
        with open(secret_file, "w", encoding="utf-8") as file:
            file.write("secret-data")

        link_path = os.path.join(self.result_dir, "linked.txt")
        try:
            os.symlink(secret_file, link_path)
        except OSError:
            self.skipTest("Cannot create symlinks on this platform")

        archive_path = os.path.join(self.temp_dir, "results.zip")
        self.module.run(
            self.mock_runner,
            {"filename": "results.zip", "files": ["result/linked.txt"]},
        )

        with zipfile.ZipFile(archive_path) as archive:
            self.assertEqual(archive.namelist(), [])

        self.mock_runner.logger.warning.assert_called_once_with(
            "Skipping symlink: %s",
            Path(link_path),
        )

    def test_run_skips_symlinked_files_in_folder(self):
        """Skip symlinked files encountered while archiving folders."""
        secret_file = os.path.join(self.temp_dir, "secret.txt")
        with open(secret_file, "w", encoding="utf-8") as file:
            file.write("secret-data")

        link_path = os.path.join(self.result_dir, "linked.txt")
        try:
            os.symlink(secret_file, link_path)
        except OSError:
            self.skipTest("Cannot create symlinks on this platform")

        self.module.run(
            self.mock_runner,
            {"filename": "results.zip", "folders": ["result"]},
        )

        with zipfile.ZipFile(os.path.join(self.temp_dir, "results.zip")) as archive:
            self.assertEqual(
                sorted(archive.namelist()),
                ["result/nested/nested.txt", "result/root.txt"],
            )

        self.mock_runner.logger.warning.assert_called_once_with(
            "Skipping symlink: %s",
            Path(link_path),
        )

    def test_run_rejects_missing_file(self):
        """Fail when a configured file does not exist."""
        with self.assertRaises(DroneException) as context:
            self.module.run(
                self.mock_runner,
                {"filename": "results.zip", "files": ["missing.txt"]},
            )

        self.assertEqual(
            str(context.exception),
            f"File not found: {Path(self.temp_dir) / 'missing.txt'}",
        )
