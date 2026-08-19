"""Tests for the archiver module."""

# These tests share symlink setup patterns with other filesystem modules.
# pylint: disable=duplicate-code,too-many-public-methods

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

    def test_run_skips_symlinked_file_when_symlinks_unavailable(self):
        """Skip symlinked files instead of packing their targets."""
        link_path = Path(self.temp_dir) / "result" / "root.txt"
        original_is_symlink = Path.is_symlink

        def fake_is_symlink(path_self):
            if path_self == link_path:
                return True
            return original_is_symlink(path_self)

        archive_path = os.path.join(self.temp_dir, "results.zip")
        with patch.object(Path, "is_symlink", fake_is_symlink):
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

    def test_run_rejects_symlinked_folder(self):
        """Reject a folders entry whose path is a directory symlink."""
        host_dir = os.path.join(self.temp_dir, "host")
        os.makedirs(host_dir)
        secret_file = os.path.join(host_dir, "job.env")
        with open(secret_file, "w", encoding="utf-8") as file:
            file.write("secret-data")

        shutil.rmtree(self.result_dir)
        try:
            os.symlink(host_dir, self.result_dir, target_is_directory=True)
        except OSError:
            self.skipTest("Cannot create directory symlinks on this platform")

        with self.assertRaises(DroneException) as context:
            self.module.run(
                self.mock_runner,
                {"filename": "results.zip", "folders": ["result"]},
            )

        self.assertEqual(
            str(context.exception),
            f"Folder must not be a symlink: {Path(self.result_dir)}",
        )

    def test_run_rejects_symlinked_folder_when_symlinks_unavailable(self):
        """Reject a folders entry reported as a directory symlink."""
        original_is_symlink = Path.is_symlink
        folder_path = Path(self.result_dir)

        def fake_is_symlink(path_self):
            if path_self == folder_path:
                return True
            return original_is_symlink(path_self)

        with patch.object(Path, "is_symlink", fake_is_symlink):
            with self.assertRaises(DroneException) as context:
                self.module.run(
                    self.mock_runner,
                    {"filename": "results.zip", "folders": ["result"]},
                )

        self.assertEqual(
            str(context.exception),
            f"Folder must not be a symlink: {folder_path}",
        )

    def test_run_skips_nested_symlinked_directory(self):
        """Do not traverse nested directory symlinks while archiving folders."""
        host_dir = os.path.join(self.temp_dir, "host")
        os.makedirs(host_dir)
        secret_file = os.path.join(host_dir, "job.env")
        with open(secret_file, "w", encoding="utf-8") as file:
            file.write("secret-data")

        link_path = os.path.join(self.result_dir, "linked_dir")
        try:
            os.symlink(host_dir, link_path, target_is_directory=True)
        except OSError:
            self.skipTest("Cannot create directory symlinks on this platform")

        self.module.run(
            self.mock_runner,
            {"filename": "results.zip", "folders": ["result"]},
        )

        with zipfile.ZipFile(os.path.join(self.temp_dir, "results.zip")) as archive:
            names = sorted(archive.namelist())
            self.assertEqual(
                names,
                ["result/nested/nested.txt", "result/root.txt"],
            )
            self.assertNotIn("result/linked_dir/job.env", names)

    def test_run_rejects_intermediate_folder_directory_symlink(self):
        """Reject a nested folders entry whose prefix is a directory symlink."""
        host_dir = os.path.join(self.temp_dir, "host")
        inner_dir = os.path.join(host_dir, "inner")
        os.makedirs(inner_dir)
        secret_file = os.path.join(inner_dir, "job.env")
        with open(secret_file, "w", encoding="utf-8") as file:
            file.write("secret-data")

        outer_link = os.path.join(self.temp_dir, "outer")
        try:
            os.symlink(host_dir, outer_link, target_is_directory=True)
        except OSError:
            self.skipTest("Cannot create directory symlinks on this platform")

        with self.assertRaises(DroneException) as context:
            self.module.run(
                self.mock_runner,
                {"filename": "results.zip", "folders": ["outer/inner"]},
            )

        self.assertEqual(
            str(context.exception),
            f"Folder must not be a symlink: {Path(outer_link)}",
        )

    def test_run_rejects_intermediate_folder_directory_symlink_when_symlinks_unavailable(
        self,
    ):
        """Reject a nested folders entry whose prefix is reported as a symlink."""
        outer_dir = Path(self.temp_dir) / "outer"
        inner_dir = outer_dir / "inner"
        inner_dir.mkdir(parents=True)
        (inner_dir / "job.env").write_text("secret-data", encoding="utf-8")
        original_is_symlink = Path.is_symlink

        def fake_is_symlink(path_self):
            if path_self == outer_dir:
                return True
            return original_is_symlink(path_self)

        with patch.object(Path, "is_symlink", fake_is_symlink):
            with self.assertRaises(DroneException) as context:
                self.module.run(
                    self.mock_runner,
                    {"filename": "results.zip", "folders": ["outer/inner"]},
                )

        self.assertEqual(
            str(context.exception),
            f"Folder must not be a symlink: {outer_dir}",
        )

    def test_run_rejects_intermediate_file_directory_symlink(self):
        """Reject a files entry whose prefix is a directory symlink."""
        host_dir = os.path.join(self.temp_dir, "host")
        os.makedirs(host_dir)
        secret_file = os.path.join(host_dir, "job.env")
        with open(secret_file, "w", encoding="utf-8") as file:
            file.write("secret-data")

        outer_link = os.path.join(self.temp_dir, "outer")
        try:
            os.symlink(host_dir, outer_link, target_is_directory=True)
        except OSError:
            self.skipTest("Cannot create directory symlinks on this platform")

        with self.assertRaises(DroneException) as context:
            self.module.run(
                self.mock_runner,
                {"filename": "results.zip", "files": ["outer/job.env"]},
            )

        self.assertEqual(
            str(context.exception),
            f"File must not be a symlink: {Path(outer_link)}",
        )

    def test_run_rejects_intermediate_file_directory_symlink_when_symlinks_unavailable(
        self,
    ):
        """Reject a files entry whose prefix is reported as a directory symlink."""
        outer_dir = Path(self.temp_dir) / "outer"
        outer_dir.mkdir()
        (outer_dir / "job.env").write_text("secret-data", encoding="utf-8")
        original_is_symlink = Path.is_symlink

        def fake_is_symlink(path_self):
            if path_self == outer_dir:
                return True
            return original_is_symlink(path_self)

        with patch.object(Path, "is_symlink", fake_is_symlink):
            with self.assertRaises(DroneException) as context:
                self.module.run(
                    self.mock_runner,
                    {"filename": "results.zip", "files": ["outer/job.env"]},
                )

        self.assertEqual(
            str(context.exception),
            f"File must not be a symlink: {outer_dir}",
        )

    def test_run_rejects_symlinked_archive_filename(self):
        """Reject an archive filename that is a file symlink."""
        host_file = os.path.join(self.temp_dir, "host-secret.txt")
        with open(host_file, "wb") as file:
            file.write(b"secret-data")

        archive_link = os.path.join(self.temp_dir, "results.zip")
        try:
            os.symlink(host_file, archive_link)
        except OSError:
            self.skipTest("Cannot create symlinks on this platform")

        with self.assertRaises(DroneException) as context:
            self.module.run(
                self.mock_runner,
                {"filename": "results.zip", "files": ["result/root.txt"]},
            )

        self.assertEqual(
            str(context.exception),
            f"Archive filename must not be a symlink: {Path(archive_link)}",
        )
        with open(host_file, "rb") as file:
            self.assertEqual(file.read(), b"secret-data")

    def test_run_rejects_symlinked_archive_filename_when_symlinks_unavailable(self):
        """Reject an archive filename reported as a file symlink."""
        archive_path = Path(self.temp_dir) / "results.zip"
        archive_path.write_text("old", encoding="utf-8")
        original_is_symlink = Path.is_symlink

        def fake_is_symlink(path_self):
            if path_self == archive_path:
                return True
            return original_is_symlink(path_self)

        with patch.object(Path, "is_symlink", fake_is_symlink):
            with self.assertRaises(DroneException) as context:
                self.module.run(
                    self.mock_runner,
                    {"filename": "results.zip", "files": ["result/root.txt"]},
                )

        self.assertEqual(
            str(context.exception),
            f"Archive filename must not be a symlink: {archive_path}",
        )
        self.assertEqual(archive_path.read_text(encoding="utf-8"), "old")

    def test_run_rejects_archive_filename_parent_directory_symlink(self):
        """Reject an archive filename whose parent directory is a symlink."""
        host_dir = os.path.join(self.temp_dir, "host")
        os.makedirs(host_dir)

        output_link = os.path.join(self.temp_dir, "output")
        try:
            os.symlink(host_dir, output_link, target_is_directory=True)
        except OSError:
            self.skipTest("Cannot create directory symlinks on this platform")

        with self.assertRaises(DroneException) as context:
            self.module.run(
                self.mock_runner,
                {
                    "filename": "output/results.zip",
                    "files": ["result/root.txt"],
                },
            )

        self.assertEqual(
            str(context.exception),
            f"Archive filename must not be a symlink: {Path(output_link)}",
        )
        self.assertFalse(os.path.exists(os.path.join(host_dir, "results.zip")))
