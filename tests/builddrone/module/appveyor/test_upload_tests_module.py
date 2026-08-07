"""Tests for the AppVeyor upload tests module."""

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch
from urllib.error import HTTPError, URLError

from builddrone.drone_exception import DroneException
from builddrone.module.appveyor.upload_tests_module import AppveyorUploadTestsModule
from builddrone.runner import Runner


class TestAppveyorUploadTestsModule(unittest.TestCase):
    """Verify AppVeyor upload behavior, validation, and retries."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.results_file = os.path.join(self.temp_dir, "xunit.xml")
        self.second_results_file = os.path.join(self.temp_dir, "junit.xml")
        with open(self.results_file, "w", encoding="utf-8") as file:
            file.write("<testsuite name='xunit'/>")
        with open(self.second_results_file, "w", encoding="utf-8") as file:
            file.write("<testsuite name='junit'/>")

        self.mock_runner = MagicMock(spec=Runner)
        self.mock_runner.logger = MagicMock()
        self.mock_runner.get_base_path.return_value = self.temp_dir
        self.module = AppveyorUploadTestsModule()
        self._job_id_patcher = patch.dict(
            os.environ, {"APPVEYOR_JOB_ID": "job-123"}, clear=False
        )
        self._job_id_patcher.start()

    def tearDown(self):
        """Clean up test fixtures."""
        self._job_id_patcher.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @staticmethod
    def _mock_response():
        mock_response = MagicMock()
        mock_response.read.return_value = b""
        mock_response.__enter__.return_value = mock_response
        mock_response.__exit__.return_value = False
        return mock_response

    @patch("builddrone.module.appveyor.upload_tests_module.urlopen")
    def test_run_uploads_relative_sources(self, mock_urlopen):
        """Upload relative results paths successfully."""
        mock_urlopen.return_value = self._mock_response()

        self.module.run(self.mock_runner, {"sources": ["xunit.xml"]})

        mock_urlopen.assert_called_once()
        request = mock_urlopen.call_args.args[0]
        self.assertEqual(
            request.full_url,
            "https://ci.appveyor.com/api/testresults/junit/job-123",
        )
        self.assertEqual(request.get_method(), "POST")
        self.assertIn(
            "multipart/form-data; boundary=", request.get_header("Content-type")
        )
        self.assertIn(b'name="file"', request.data)
        self.assertIn(b"<testsuite name='xunit'/>", request.data)
        self.assertEqual(
            mock_urlopen.call_args.kwargs["timeout"],
            self.module._http_timeout,
        )

    @patch("builddrone.module.appveyor.upload_tests_module.urlopen")
    def test_run_uploads_multiple_sources(self, mock_urlopen):
        """Upload each configured results file."""
        mock_urlopen.return_value = self._mock_response()

        self.module.run(
            self.mock_runner,
            {"sources": ["xunit.xml", "junit.xml"]},
        )

        self.assertEqual(mock_urlopen.call_count, 2)
        payloads = [call.args[0].data for call in mock_urlopen.call_args_list]
        self.assertTrue(any(b"<testsuite name='xunit'/>" in data for data in payloads))
        self.assertTrue(any(b"<testsuite name='junit'/>" in data for data in payloads))

    @patch("builddrone.module.appveyor.upload_tests_module.urlopen")
    def test_run_uploads_absolute_sources(self, mock_urlopen):
        """Upload absolute results paths successfully."""
        mock_urlopen.return_value = self._mock_response()

        self.module.run(self.mock_runner, {"sources": [self.results_file]})

        mock_urlopen.assert_called_once()

    def test_run_requires_sources(self):
        """Reject missing or empty sources."""
        with self.assertRaises(DroneException) as context:
            self.module.run(self.mock_runner, {})

        self.assertEqual(
            str(context.exception), "Argument 'sources' must be a non-empty list"
        )

    def test_run_rejects_invalid_source_entries(self):
        """Reject non-string or blank source entries."""
        with self.assertRaises(DroneException) as context:
            self.module.run(self.mock_runner, {"sources": ["xunit.xml", ""]})

        self.assertEqual(
            str(context.exception),
            "Argument 'sources' must contain non-empty strings",
        )

    def test_run_rejects_invalid_repeat(self):
        """Reject non-positive repeat values."""
        with self.assertRaises(DroneException) as context:
            self.module.run(
                self.mock_runner, {"sources": ["xunit.xml"], "repeat": 0}
            )

        self.assertEqual(
            str(context.exception), "Argument 'repeat' must be a positive integer"
        )

    def test_run_rejects_invalid_timeout(self):
        """Reject non-positive timeout values."""
        with self.assertRaises(DroneException) as context:
            self.module.run(
                self.mock_runner, {"sources": ["xunit.xml"], "timeout": True}
            )

        self.assertEqual(
            str(context.exception), "Argument 'timeout' must be a positive integer"
        )

    def test_run_requires_job_id(self):
        """Fail when APPVEYOR_JOB_ID is unset."""
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(DroneException) as context:
                self.module.run(self.mock_runner, {"sources": ["xunit.xml"]})

        self.assertEqual(
            str(context.exception),
            "Environment variable APPVEYOR_JOB_ID is not set",
        )

    def test_run_requires_existing_file(self):
        """Fail when a results file does not exist."""
        with self.assertRaises(DroneException) as context:
            self.module.run(self.mock_runner, {"sources": ["missing.xml"]})

        self.assertEqual(
            str(context.exception),
            f"Test results file not found: {Path(self.temp_dir) / 'missing.xml'}",
        )

    @patch("builddrone.module.appveyor.upload_tests_module.time.sleep")
    @patch("builddrone.module.appveyor.upload_tests_module.urlopen")
    def test_run_retries_then_succeeds(self, mock_urlopen, mock_sleep):
        """Retry after failure and succeed on a later attempt."""
        mock_urlopen.side_effect = [
            URLError("temporary failure"),
            self._mock_response(),
        ]

        self.module.run(
            self.mock_runner,
            {"sources": ["xunit.xml"], "repeat": 3, "timeout": 7},
        )

        self.assertEqual(mock_urlopen.call_count, 2)
        mock_sleep.assert_called_once_with(7)

    @patch("builddrone.module.appveyor.upload_tests_module.time.sleep")
    @patch("builddrone.module.appveyor.upload_tests_module.urlopen")
    def test_run_fails_after_repeat_exhausted(self, mock_urlopen, mock_sleep):
        """Fail after the configured number of attempts."""
        mock_urlopen.side_effect = URLError("still failing")

        with self.assertRaises(DroneException) as context:
            self.module.run(
                self.mock_runner,
                {"sources": ["xunit.xml"], "repeat": 2, "timeout": 4},
            )

        self.assertEqual(mock_urlopen.call_count, 2)
        mock_sleep.assert_called_once_with(4)
        self.assertIn(
            "Failed to upload test results to AppVeyor after 2 attempt(s)",
            str(context.exception),
        )

    @patch("builddrone.module.appveyor.upload_tests_module.time.sleep")
    @patch("builddrone.module.appveyor.upload_tests_module.urlopen")
    def test_run_defaults_to_single_attempt(self, mock_urlopen, mock_sleep):
        """Use a single attempt when repeat is omitted."""
        mock_urlopen.side_effect = HTTPError(
            "https://ci.appveyor.com/api/testresults/junit/job-123",
            500,
            "Server Error",
            hdrs=None,
            fp=mock_open(read_data=b"")(),
        )

        with self.assertRaises(DroneException):
            self.module.run(self.mock_runner, {"sources": ["xunit.xml"]})

        self.assertEqual(mock_urlopen.call_count, 1)
        mock_sleep.assert_not_called()
