"""Tests for the Builddrone runner."""

import logging
import unittest
from unittest.mock import MagicMock, patch

from builddrone.drone_exception import DroneException
from builddrone.runner import Runner


class TestRunner(unittest.TestCase):
    """Verify runner behavior."""

    @patch("builddrone.runner.logging.getLogger")
    @patch("builddrone.runner.logging.basicConfig")
    @patch("builddrone.runner.subprocess.run")
    def test_init_sets_python_executable(
        self, mock_subprocess_run, mock_basic_config, mock_get_logger
    ):
        """Runner should initialize with the current Python executable."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_subprocess_run.return_value = MagicMock(returncode=0)

        runner = Runner()

        mock_basic_config.assert_called_once_with(level=logging.INFO)
        mock_get_logger.assert_called_once_with("builddrone.runner")
        self.assertIs(runner.logger, mock_logger)
        runner.run(["-V"])
        mock_subprocess_run.assert_called_once()

    @patch("builddrone.runner.logging.getLogger")
    @patch("builddrone.runner.logging.basicConfig")
    @patch("builddrone.runner.sys.executable", "")
    def test_init_without_python_executable_raises(
        self, mock_basic_config, mock_get_logger
    ):
        """Runner should fail when no Python executable is available."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        with self.assertRaises(DroneException) as context:
            Runner()

        mock_basic_config.assert_called_once_with(level=logging.INFO)
        mock_get_logger.assert_called_once_with("builddrone.runner")
        self.assertEqual(str(context.exception), "Python executable not found")

    @patch("builddrone.runner.os.path.isfile")
    @patch("builddrone.runner.os.path.exists")
    @patch("builddrone.runner.logging.getLogger")
    @patch("builddrone.runner.logging.basicConfig")
    def test_set_runner_updates_python_path(
        self, _mock_basic_config, mock_get_logger, mock_exists, mock_isfile
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
    @patch("builddrone.runner.logging.getLogger")
    @patch("builddrone.runner.logging.basicConfig")
    def test_set_runner_ignores_invalid_path(
        self, _mock_basic_config, mock_get_logger, mock_exists, mock_isfile
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
    @patch("builddrone.runner.logging.getLogger")
    @patch("builddrone.runner.logging.basicConfig")
    def test_reset_runner_restores_current_executable(
        self, _mock_basic_config, mock_get_logger
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
    @patch("builddrone.runner.logging.getLogger")
    @patch("builddrone.runner.logging.basicConfig")
    def test_run_executes_python_command(
        self, _mock_basic_config, mock_get_logger, mock_subprocess_run
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
