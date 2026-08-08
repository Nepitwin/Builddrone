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
        self.assertIn(str(artifact_path), command[3])
        self.assertIn('-FileName "results.zip"', command[3])
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
