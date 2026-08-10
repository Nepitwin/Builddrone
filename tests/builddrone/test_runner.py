"""Tests for the Builddrone runner."""

import logging
import sys
import unittest
from unittest.mock import MagicMock, patch

from builddrone.drone_exception import DroneException
from builddrone.runner import Runner, configure_logging, _LOG_FORMAT


class TestRunner(unittest.TestCase):
    """Verify runner behavior."""

    @patch("builddrone.runner.configure_logging")
    @patch("builddrone.runner.logging.getLogger")
    @patch("builddrone.runner.subprocess.run")
    def test_init_sets_python_executable(
        self, mock_subprocess_run, mock_get_logger, mock_configure_logging
    ):
        """Runner should initialize with the current Python executable."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_subprocess_run.return_value = MagicMock(returncode=0)

        runner = Runner()

        mock_configure_logging.assert_called_once_with()
        mock_get_logger.assert_called_once_with("builddrone.runner")
        self.assertIs(runner.logger, mock_logger)
        runner.run(["-V"])
        mock_subprocess_run.assert_called_once()

    @patch("builddrone.runner.configure_logging")
    @patch("builddrone.runner.logging.getLogger")
    @patch("builddrone.runner.sys.executable", "")
    def test_init_without_python_executable_raises(
        self, mock_get_logger, mock_configure_logging
    ):
        """Runner should fail when no Python executable is available."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        with self.assertRaises(DroneException) as context:
            Runner()

        mock_configure_logging.assert_called_once_with()
        mock_get_logger.assert_called_once_with("builddrone.runner")
        self.assertEqual(str(context.exception), "Python executable not found")

    def test_configure_logging_writes_to_stdout(self):
        """Logging should use stdout so PowerShell does not treat INFO as errors."""
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        configure_logging()

        self.assertEqual(len(root_logger.handlers), 1)
        handler = root_logger.handlers[0]
        self.assertIsInstance(handler, logging.StreamHandler)
        self.assertIs(handler.stream, sys.stdout)
        self.assertEqual(handler.formatter._fmt, _LOG_FORMAT)

    @patch("builddrone.runner.os.path.isfile")
    @patch("builddrone.runner.os.path.exists")
    @patch("builddrone.runner.configure_logging")
    @patch("builddrone.runner.logging.getLogger")
    def test_set_runner_updates_python_path(
        self, mock_get_logger, _mock_configure_logging, mock_exists, mock_isfile
    ):
        """set_runner should update the interpreter when the path is valid."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_exists.return_value = True
        mock_isfile.return_value = True
        with patch("builddrone.runner.subprocess.run") as mock_subprocess_run:
            mock_subprocess_run.return_value = MagicMock(returncode=0)
            runner = Runner()
            runner.set_runner("C:/Python/python.exe")
            runner.run(["-V"])

        mock_subprocess_run.assert_called_once_with(
            ["C:/Python/python.exe", "-V"],
            cwd=None,
            check=False,
        )

    @patch("builddrone.runner.os.path.isfile")
    @patch("builddrone.runner.os.path.exists")
    @patch("builddrone.runner.sys.executable", "C:/Python/python.exe")
    @patch("builddrone.runner.configure_logging")
    @patch("builddrone.runner.logging.getLogger")
    def test_set_runner_ignores_invalid_path(
        self, mock_get_logger, _mock_configure_logging, mock_exists, mock_isfile
    ):
        """set_runner should ignore invalid paths."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_exists.return_value = False
        mock_isfile.return_value = False
        with patch("builddrone.runner.subprocess.run") as mock_subprocess_run:
            mock_subprocess_run.return_value = MagicMock(returncode=0)
            runner = Runner()
            original_command = ["-V"]
            runner.set_runner("C:/missing/python.exe")
            runner.run(original_command)

        mock_subprocess_run.assert_called_once_with(
            ["C:/Python/python.exe", "-V"],
            cwd=None,
            check=False,
        )

    @patch("builddrone.runner.sys.executable", "C:/Python/python.exe")
    @patch("builddrone.runner.configure_logging")
    @patch("builddrone.runner.logging.getLogger")
    def test_reset_runner_restores_current_executable(
        self, mock_get_logger, _mock_configure_logging
    ):
        """reset_runner should restore sys.executable."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        with patch("builddrone.runner.subprocess.run") as mock_subprocess_run:
            mock_subprocess_run.return_value = MagicMock(returncode=0)
            runner = Runner()
            runner.set_runner("C:/other/python.exe")
            runner.reset_runner()
            runner.run(["-V"])

        mock_subprocess_run.assert_called_once_with(
            ["C:/Python/python.exe", "-V"],
            cwd=None,
            check=False,
        )

    @patch("builddrone.runner.subprocess.run")
    @patch("builddrone.runner.sys.executable", "C:/Python/python.exe")
    @patch("builddrone.runner.configure_logging")
    @patch("builddrone.runner.logging.getLogger")
    def test_run_executes_python_command(
        self, mock_get_logger, _mock_configure_logging, mock_subprocess_run
    ):
        """run should execute the configured interpreter with the command."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_result = MagicMock(returncode=7)
        mock_subprocess_run.return_value = mock_result

        runner = Runner()
        exit_code = runner.run(["-m", "pylint", "src/builddrone"], cwd="C:/repo")

        self.assertEqual(exit_code, 7)
        mock_subprocess_run.assert_called_once_with(
            ["C:/Python/python.exe", "-m", "pylint", "src/builddrone"],
            cwd="C:/repo",
            check=False,
        )
