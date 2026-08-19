"""Tests for the twine upload module."""

# These tests share file-list validation patterns with other upload modules.
# pylint: disable=duplicate-code

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from builddrone.drone_exception import DroneException
from builddrone.module.twine.upload_module import TwineUploadModule
from builddrone.runner import Runner


class TestTwineUploadModule(unittest.TestCase):
    """Verify twine upload behavior and validation."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.dist_dir = os.path.join(self.temp_dir, "dist")
        os.makedirs(self.dist_dir, exist_ok=True)

        self.wheel_file = os.path.join(self.dist_dir, "example-1.0.0-py3-none-any.whl")
        self.sdist_file = os.path.join(self.dist_dir, "example-1.0.0.tar.gz")
        with open(self.wheel_file, "wb") as file:
            file.write(b"wheel-content")
        with open(self.sdist_file, "wb") as file:
            file.write(b"sdist-content")

        self.mock_runner = MagicMock(spec=Runner)
        self.mock_runner.logger = MagicMock()
        self.mock_runner.get_base_path.return_value = Path(self.temp_dir)
        self.module = TwineUploadModule()

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_run_uploads_each_glob_pattern(self):
        """Upload matched files for each configured glob pattern."""
        self.mock_runner.run.side_effect = [0, 0, 0]

        self.module.run(
            self.mock_runner,
            {"files": ["dist/*.whl", "dist/*.tar.gz"]},
        )

        self.assertEqual(self.mock_runner.run.call_count, 3)
        self.mock_runner.run.assert_any_call(
            ["-m", "twine", "--version"],
            cwd=self.temp_dir,
        )
        self.mock_runner.run.assert_any_call(
            [
                "-m",
                "twine",
                "upload",
                "--skip-existing",
                self.wheel_file,
            ],
            cwd=self.temp_dir,
        )
        self.mock_runner.run.assert_any_call(
            [
                "-m",
                "twine",
                "upload",
                "--skip-existing",
                self.sdist_file,
            ],
            cwd=self.temp_dir,
        )

    def test_run_uploads_multiple_files_for_one_pattern(self):
        """Upload all files that match a single glob pattern."""
        second_wheel = os.path.join(self.dist_dir, "example-2.0.0-py3-none-any.whl")
        with open(second_wheel, "wb") as file:
            file.write(b"wheel-content-2")
        self.mock_runner.run.side_effect = [0, 0]

        self.module.run(self.mock_runner, {"files": ["dist/*.whl"]})

        upload_call = self.mock_runner.run.call_args_list[-1]
        uploaded_files = upload_call.args[0][4:]
        self.assertEqual(
            uploaded_files,
            [self.wheel_file, second_wheel],
        )

    def test_run_supports_repository_argument(self):
        """Pass an optional repository URL to twine."""
        self.mock_runner.run.side_effect = [0, 0]

        self.module.run(
            self.mock_runner,
            {
                "files": ["dist/*.whl"],
                "repository": "https://upload.pypi.org/legacy/",
            },
        )

        self.mock_runner.run.assert_any_call(
            [
                "-m",
                "twine",
                "upload",
                "--skip-existing",
                "--repository-url",
                "https://upload.pypi.org/legacy/",
                self.wheel_file,
            ],
            cwd=self.temp_dir,
        )

    def test_run_enables_skip_existing_by_default(self):
        """Pass --skip-existing when skip_existing is omitted."""
        self.mock_runner.run.side_effect = [0, 0]

        self.module.run(self.mock_runner, {"files": ["dist/*.whl"]})

        self.mock_runner.run.assert_any_call(
            ["-m", "twine", "upload", "--skip-existing", self.wheel_file],
            cwd=self.temp_dir,
        )

    def test_run_can_enable_skip_existing_explicitly(self):
        """Pass --skip-existing when skip_existing is true."""
        self.mock_runner.run.side_effect = [0, 0]

        self.module.run(
            self.mock_runner,
            {"files": ["dist/*.whl"], "skip_existing": True},
        )

        self.mock_runner.run.assert_any_call(
            ["-m", "twine", "upload", "--skip-existing", self.wheel_file],
            cwd=self.temp_dir,
        )

    def test_run_can_disable_skip_existing(self):
        """Omit --skip-existing when configured to false."""
        self.mock_runner.run.side_effect = [0, 0]

        self.module.run(
            self.mock_runner,
            {"files": ["dist/*.whl"], "skip_existing": False},
        )

        self.mock_runner.run.assert_any_call(
            ["-m", "twine", "upload", self.wheel_file],
            cwd=self.temp_dir,
        )

    def test_run_requires_files(self):
        """Reject missing or empty files."""
        with self.assertRaises(DroneException) as context:
            self.module.run(self.mock_runner, {})

        self.assertEqual(
            str(context.exception),
            "Argument 'files' must be a non-empty list",
        )

    def test_run_rejects_invalid_file_entries(self):
        """Reject non-string or blank file entries."""
        with self.assertRaises(DroneException) as context:
            self.module.run(self.mock_runner, {"files": ["dist/*.whl", ""]})

        self.assertEqual(
            str(context.exception),
            "Argument 'files' must contain non-empty strings",
        )

    def test_run_rejects_invalid_skip_existing(self):
        """Reject non-boolean skip_existing values."""
        with self.assertRaises(DroneException) as context:
            self.module.run(
                self.mock_runner,
                {"files": ["dist/*.whl"], "skip_existing": "true"},
            )

        self.assertEqual(
            str(context.exception),
            "Argument 'skip_existing' must be a boolean",
        )

    def test_run_rejects_invalid_repository(self):
        """Reject blank repository values."""
        with self.assertRaises(DroneException) as context:
            self.module.run(
                self.mock_runner,
                {"files": ["dist/*.whl"], "repository": "  "},
            )

        self.assertEqual(
            str(context.exception),
            "Argument 'repository' must be a non-empty string",
        )

    def test_run_requires_matching_files(self):
        """Fail when a glob pattern matches no files."""
        self.mock_runner.run.return_value = 0

        with self.assertRaises(DroneException) as context:
            self.module.run(self.mock_runner, {"files": ["dist/*.zip"]})

        self.assertEqual(
            str(context.exception),
            "No files matched pattern: dist/*.zip",
        )

    def test_run_raises_when_twine_is_not_installed(self):
        """Fail before upload when twine is unavailable."""
        self.mock_runner.run.return_value = 1

        with self.assertRaises(DroneException) as context:
            self.module.run(self.mock_runner, {"files": ["dist/*.whl"]})

        self.assertEqual(str(context.exception), "twine is not installed")
        self.mock_runner.run.assert_called_once_with(
            ["-m", "twine", "--version"],
            cwd=self.temp_dir,
        )

    def test_run_fails_on_non_zero_exit_code(self):
        """Surface twine upload failures."""
        self.mock_runner.run.side_effect = [0, 1]

        with self.assertRaises(DroneException) as context:
            self.module.run(self.mock_runner, {"files": ["dist/*.whl"]})

        self.assertEqual(
            str(context.exception),
            "Twine upload failed for pattern 'dist/*.whl' with exit code 1",
        )

    def test_run_rejects_symlink_matches(self):
        """Reject symlinked files matched by upload globs."""
        secret_file = os.path.join(self.temp_dir, "secret.txt")
        with open(secret_file, "w", encoding="utf-8") as file:
            file.write("secret-data")

        link_path = os.path.join(self.dist_dir, "evil-1.0.0-py3-none-any.whl")
        try:
            os.symlink(secret_file, link_path)
        except OSError:
            self.skipTest("Cannot create symlinks on this platform")

        self.mock_runner.run.return_value = 0

        with self.assertRaises(DroneException) as context:
            self.module.run(self.mock_runner, {"files": ["dist/*.whl"]})

        self.assertEqual(
            str(context.exception),
            f"Upload file must not be a symlink: {Path(link_path)}",
        )
        self.mock_runner.run.assert_called_once_with(
            ["-m", "twine", "--version"],
            cwd=self.temp_dir,
        )

    def test_run_rejects_glob_through_directory_symlink(self):
        """Reject glob matches whose prefix is a directory symlink."""
        host_dir = os.path.join(self.temp_dir, "host")
        os.makedirs(host_dir)
        secret_wheel = os.path.join(host_dir, "secret-1.0.0-py3-none-any.whl")
        with open(secret_wheel, "wb") as file:
            file.write(b"secret-data")

        shutil.rmtree(self.dist_dir)
        try:
            os.symlink(host_dir, self.dist_dir, target_is_directory=True)
        except OSError:
            self.skipTest("Cannot create directory symlinks on this platform")

        self.mock_runner.run.return_value = 0

        with self.assertRaises(DroneException) as context:
            self.module.run(self.mock_runner, {"files": ["dist/*.whl"]})

        self.assertEqual(
            str(context.exception),
            f"Upload file must not be a symlink: {Path(self.dist_dir)}",
        )
        self.mock_runner.run.assert_called_once_with(
            ["-m", "twine", "--version"],
            cwd=self.temp_dir,
        )

    def test_run_rejects_glob_through_directory_symlink_when_symlinks_unavailable(self):
        """Reject glob matches whose prefix is reported as a directory symlink."""
        dist_path = Path(self.dist_dir)
        original_is_symlink = Path.is_symlink

        def fake_is_symlink(path_self):
            if path_self == dist_path:
                return True
            return original_is_symlink(path_self)

        self.mock_runner.run.return_value = 0
        with patch.object(Path, "is_symlink", fake_is_symlink):
            with self.assertRaises(DroneException) as context:
                self.module.run(self.mock_runner, {"files": ["dist/*.whl"]})

        self.assertEqual(
            str(context.exception),
            f"Upload file must not be a symlink: {dist_path}",
        )
        self.mock_runner.run.assert_called_once_with(
            ["-m", "twine", "--version"],
            cwd=self.temp_dir,
        )
