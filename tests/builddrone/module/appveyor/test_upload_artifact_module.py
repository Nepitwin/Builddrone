"""Tests for the AppVeyor upload artifact module."""

# These tests share file-list validation patterns with other upload modules.
# pylint: disable=duplicate-code

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from builddrone.drone_exception import DroneException
from builddrone.module.appveyor.upload_artifact_module import (
    AppveyorUploadArtifactModule,
)
from builddrone.runner import Runner


class TestAppveyorUploadArtifactModule(unittest.TestCase):
    """Verify artifact upload behavior and validation."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.artifact_file = os.path.join(self.temp_dir, "results.zip")
        with open(self.artifact_file, "wb") as file:
            file.write(b"zip-content")

        self.mock_runner = MagicMock(spec=Runner)
        self.mock_runner.logger = MagicMock()
        self.mock_runner.get_base_path.return_value = self.temp_dir
        self.module = AppveyorUploadArtifactModule()

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("builddrone.module.appveyor.upload_artifact_module.subprocess.run")
    def test_run_uploads_relative_files(self, mock_run):
        """Upload relative artifact paths with Push-AppveyorArtifact."""
        mock_run.return_value = MagicMock(returncode=0)

        self.module.run(self.mock_runner, {"files": ["results.zip"]})

        mock_run.assert_called_once()
        command = mock_run.call_args.args[0]
        artifact_path = Path(self.temp_dir) / "results.zip"
        self.assertEqual(command[0], "powershell")
        self.assertEqual(command[1], "-NoProfile")
        self.assertEqual(command[2], "-Command")
        self.assertIn(f"'{artifact_path}'", command[3])
        self.assertIn("-FileName 'results.zip'", command[3])
        self.assertEqual(
            mock_run.call_args.kwargs["cwd"],
            self.temp_dir,
        )

    @patch("builddrone.module.appveyor.upload_artifact_module.subprocess.run")
    def test_run_uploads_multiple_files(self, mock_run):
        """Upload each configured artifact file."""
        second_artifact = os.path.join(self.temp_dir, "debug.log")
        with open(second_artifact, "w", encoding="utf-8") as file:
            file.write("debug")
        mock_run.return_value = MagicMock(returncode=0)

        self.module.run(self.mock_runner, {"files": ["results.zip", "debug.log"]})

        self.assertEqual(mock_run.call_count, 2)

    @patch("builddrone.module.appveyor.upload_artifact_module.subprocess.run")
    def test_run_uploads_absolute_files(self, mock_run):
        """Upload absolute artifact paths successfully."""
        mock_run.return_value = MagicMock(returncode=0)

        self.module.run(self.mock_runner, {"files": [self.artifact_file]})

        mock_run.assert_called_once()

    @patch("builddrone.module.appveyor.upload_artifact_module.subprocess.run")
    def test_run_escapes_powershell_metacharacters(self, mock_run):
        """Quote artifact paths so they cannot inject PowerShell commands."""
        malicious_name = "evil'$()whoami'.zip"
        malicious_path = os.path.join(self.temp_dir, malicious_name)
        with open(malicious_path, "wb") as file:
            file.write(b"x")
        mock_run.return_value = MagicMock(returncode=0)

        self.module.run(self.mock_runner, {"files": [malicious_name]})

        command = mock_run.call_args.args[0][3]
        self.assertIn("-FileName 'evil''$()whoami''.zip'", command)
        self.assertNotRegex(command, r'-Path "[^"]*"')
        self.assertIn("evil''$()whoami''.zip'", command)

    def test_ps_single_quoted_escapes_injection_payloads(self):
        """Single-quote PowerShell literals for metacharacter-heavy values."""
        cases = [
            ('evil"; Write-Host injected; "', """'evil"; Write-Host injected; "'"""),
            ("evil'$()whoami'", "'evil''$()whoami'''"),
            ("path'with'quotes", "'path''with''quotes'"),
        ]
        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(
                    AppveyorUploadArtifactModule._ps_single_quoted(  # pylint: disable=protected-access
                        value
                    ),
                    expected,
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
            self.module.run(self.mock_runner, {"files": ["results.zip", ""]})

        self.assertEqual(
            str(context.exception),
            "Argument 'files' must contain non-empty strings",
        )

    def test_run_requires_existing_file(self):
        """Fail when an artifact file does not exist."""
        with self.assertRaises(DroneException) as context:
            self.module.run(self.mock_runner, {"files": ["missing.zip"]})

        self.assertEqual(
            str(context.exception),
            f"Artifact file not found: {Path(self.temp_dir) / 'missing.zip'}",
        )

    def test_run_rejects_symlink(self):
        """Reject a listed artifact path that is a symlink."""
        secret_file = os.path.join(self.temp_dir, "secret.txt")
        with open(secret_file, "w", encoding="utf-8") as file:
            file.write("secret-data")

        link_path = os.path.join(self.temp_dir, "linked.zip")
        try:
            os.symlink(secret_file, link_path)
        except OSError:
            self.skipTest("Cannot create symlinks on this platform")

        with self.assertRaises(DroneException) as context:
            self.module.run(self.mock_runner, {"files": ["linked.zip"]})

        self.assertEqual(
            str(context.exception),
            f"Artifact file must not be a symlink: {Path(link_path)}",
        )

    def test_run_rejects_symlink_when_symlinks_unavailable(self):
        """Reject an artifact path reported as a symlink."""
        artifact_path = Path(self.artifact_file)
        original_is_symlink = Path.is_symlink

        def fake_is_symlink(path_self):
            if path_self == artifact_path:
                return True
            return original_is_symlink(path_self)

        with patch.object(Path, "is_symlink", fake_is_symlink):
            with self.assertRaises(DroneException) as context:
                self.module.run(self.mock_runner, {"files": ["results.zip"]})

        self.assertEqual(
            str(context.exception),
            f"Artifact file must not be a symlink: {artifact_path}",
        )

    def test_run_rejects_intermediate_directory_symlink(self):
        """Reject artifact paths whose prefix is a directory symlink."""
        host_dir = os.path.join(self.temp_dir, "host")
        os.makedirs(host_dir)
        secret_file = os.path.join(host_dir, "results.zip")
        with open(secret_file, "wb") as file:
            file.write(b"secret-data")

        artifacts_dir = os.path.join(self.temp_dir, "artifacts")
        try:
            os.symlink(host_dir, artifacts_dir, target_is_directory=True)
        except OSError:
            self.skipTest("Cannot create directory symlinks on this platform")

        with self.assertRaises(DroneException) as context:
            self.module.run(self.mock_runner, {"files": ["artifacts/results.zip"]})

        self.assertEqual(
            str(context.exception),
            f"Artifact file must not be a symlink: {Path(artifacts_dir)}",
        )

    def test_run_rejects_intermediate_directory_symlink_when_symlinks_unavailable(self):
        """Reject artifact paths whose prefix is reported as a directory symlink."""
        artifacts_dir = Path(self.temp_dir) / "artifacts"
        artifacts_dir.mkdir()
        artifact_file = artifacts_dir / "results.zip"
        artifact_file.write_bytes(b"secret-data")
        original_is_symlink = Path.is_symlink

        def fake_is_symlink(path_self):
            if path_self == artifacts_dir:
                return True
            return original_is_symlink(path_self)

        with patch.object(Path, "is_symlink", fake_is_symlink):
            with self.assertRaises(DroneException) as context:
                self.module.run(self.mock_runner, {"files": ["artifacts/results.zip"]})

        self.assertEqual(
            str(context.exception),
            f"Artifact file must not be a symlink: {artifacts_dir}",
        )

    @patch("builddrone.module.appveyor.upload_artifact_module.subprocess.run")
    def test_run_fails_on_non_zero_exit_code(self, mock_run):
        """Surface Push-AppveyorArtifact failures."""
        mock_run.return_value = MagicMock(returncode=1)

        with self.assertRaises(DroneException) as context:
            self.module.run(self.mock_runner, {"files": ["results.zip"]})

        self.assertIn(
            "Failed to upload AppVeyor artifact",
            str(context.exception),
        )
        self.assertIn("exit code 1", str(context.exception))

    @patch("builddrone.module.appveyor.upload_artifact_module.subprocess.run")
    def test_run_fails_when_powershell_is_unavailable(self, mock_run):
        """Surface subprocess failures when PowerShell cannot be started."""
        mock_run.side_effect = OSError("powershell not found")

        with self.assertRaises(DroneException) as context:
            self.module.run(self.mock_runner, {"files": ["results.zip"]})

        self.assertIn(
            "Failed to upload AppVeyor artifact",
            str(context.exception),
        )
