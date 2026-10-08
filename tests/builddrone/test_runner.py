"""Tests for the Builddrone runner."""

import logging
import os
import subprocess
import sys
import tempfile
import unittest
import venv
from pathlib import Path
from unittest.mock import MagicMock, patch

from builddrone.drone_exception import DroneException
from builddrone.runner import (  # pylint: disable=protected-access
    _SAFE_MODULE_LAUNCHER,
    Runner,
    _python_command,
    configure_logging,
)

_SHADOW_MODULE = """\
open('pwned', 'w', encoding='utf-8').write('leaked')
raise SystemExit(86)
"""


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
        record = logging.LogRecord(
            name="builddrone.runner",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="test message",
            args=(),
            exc_info=None,
        )
        self.assertEqual(
            handler.formatter.format(record),
            "INFO:builddrone.runner:test message",
        )

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
            stderr=subprocess.STDOUT,
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
            stderr=subprocess.STDOUT,
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
            stderr=subprocess.STDOUT,
        )

    @patch("builddrone.runner.sys.version_info", (3, 11, 0))
    @patch("builddrone.runner.subprocess.run")
    @patch("builddrone.runner.sys.executable", "C:/Python/python.exe")
    @patch("builddrone.runner.configure_logging")
    @patch("builddrone.runner.logging.getLogger")
    def test_run_module_inserts_safe_path_flag(
        self, mock_get_logger, _mock_configure_logging, mock_subprocess_run
    ):
        """Python 3.11+ module runs pass -P before -m."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_subprocess_run.return_value = MagicMock(returncode=7)

        runner = Runner()
        exit_code = runner.run(
            ["-m", "pip", "install", "-r", "requirements.txt"], cwd="C:/repo"
        )

        self.assertEqual(exit_code, 7)
        mock_subprocess_run.assert_called_once_with(
            [
                "C:/Python/python.exe",
                "-P",
                "-m",
                "pip",
                "install",
                "-r",
                "requirements.txt",
            ],
            cwd="C:/repo",
            check=False,
            stderr=subprocess.STDOUT,
        )

    @patch("builddrone.runner.sys.version_info", (3, 10, 11))
    @patch("builddrone.runner.subprocess.run")
    @patch("builddrone.runner.sys.executable", "C:/Python/python.exe")
    @patch("builddrone.runner.configure_logging")
    @patch("builddrone.runner.logging.getLogger")
    def test_run_module_scrubs_path_before_python_311(
        self, mock_get_logger, _mock_configure_logging, mock_subprocess_run
    ):
        """Python 3.8–3.10 drop the working directory before runpy."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_subprocess_run.return_value = MagicMock(returncode=7)

        runner = Runner()
        exit_code = runner.run(["-m", "pylint", "src/builddrone"], cwd="C:/repo")

        self.assertEqual(exit_code, 7)
        mock_subprocess_run.assert_called_once_with(
            [
                "C:/Python/python.exe",
                "-S",
                "-c",
                _SAFE_MODULE_LAUNCHER,
                "pylint",
                "src/builddrone",
            ],
            cwd="C:/repo",
            check=False,
            stderr=subprocess.STDOUT,
        )

    def test_python_command_leaves_scripts_unchanged(self):
        """Script execution does not gain -P or the module launcher."""
        self.assertEqual(
            _python_command("C:/Python/python.exe", ["tool.py"], (3, 12, 0)),
            ["C:/Python/python.exe", "tool.py"],
        )
        self.assertNotIn(
            "-I",
            _python_command("C:/Python/python.exe", ["-m", "pip"], (3, 11, 0)),
        )

    def test_safe_launcher_ignores_workspace_modules(self):
        """The 3.8–3.10 launcher runs the installed module, not a workspace file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._plant_shadow_modules(root)
            nested = root / "nested"
            nested.mkdir()
            env = os.environ.copy()
            env["PYTHONPATH"] = os.pathsep.join((str(root), str(nested / "..")))

            result = subprocess.run(
                [sys.executable, "-S", "-c", _SAFE_MODULE_LAUNCHER, "calendar", "1999"],
                cwd=root,
                env=env,
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("1999", result.stdout)
            self.assertNotIn("leaked", result.stdout)
            self.assertFalse((root / "pwned").exists())

    def test_run_ignores_workspace_module_after_venv(self):
        """A root pip.py does not run when the venv interpreter installs packages."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self._plant_shadow_modules(root)
            venv_path = root / ".venv"
            venv.create(venv_path, with_pip=True, symlinks=False)
            python_executable = self._venv_python(venv_path)

            runner = Runner()
            runner.set_runner(str(python_executable))
            exit_code = runner.run(["-m", "pip", "--version"], cwd=str(root))

            self.assertEqual(exit_code, 0)
            self.assertFalse((root / "pwned").exists())

    def test_run_script_returns_exit_code(self):
        """Running a source file still returns that file's exit code."""
        with tempfile.TemporaryDirectory() as temp_dir:
            script = Path(temp_dir) / "tool.py"
            script.write_text("raise SystemExit(5)\n", encoding="utf-8")

            runner = Runner()
            exit_code = runner.run([str(script)], cwd=temp_dir)

        self.assertEqual(exit_code, 5)

    @patch("builddrone.runner.subprocess.run")
    @patch("builddrone.runner.sys.executable", "C:/Python/python.exe")
    @patch("builddrone.runner.configure_logging")
    @patch("builddrone.runner.logging.getLogger")
    def test_run_command_executes_without_a_shell(
        self, mock_get_logger, _mock_configure_logging, mock_subprocess_run
    ):
        """External commands keep their arguments and do not use a shell."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        mock_subprocess_run.return_value = MagicMock(returncode=3)

        runner = Runner()
        exit_code = runner.run_command(["dotnet", "build", "App.csproj"], cwd="C:/repo")

        self.assertEqual(exit_code, 3)
        mock_subprocess_run.assert_called_once_with(
            ["dotnet", "build", "App.csproj"],
            cwd="C:/repo",
            check=False,
            shell=False,
            stderr=subprocess.STDOUT,
        )

    def test_run_command_rejects_empty_command(self):
        """Reject a command that has no arguments."""
        runner = Runner()

        with self.assertRaises(DroneException) as context:
            runner.run_command([])

        self.assertEqual(str(context.exception), "Command must be a non-empty list")

    def test_run_command_rejects_blank_argument(self):
        """Reject a command argument that is an empty string."""
        runner = Runner()

        with self.assertRaises(DroneException) as context:
            runner.run_command(["dotnet", ""])

        self.assertEqual(
            str(context.exception), "Command must contain non-empty strings"
        )

    @staticmethod
    def _plant_shadow_modules(root: Path) -> None:
        """Plant workspace files that would shadow python -m targets."""
        for name in (
            "pip.py",
            "build.py",
            "pylint.py",
            "twine.py",
            "robot.py",
            "calendar.py",
            "site.py",
            "os.py",
            "runpy.py",
        ):
            (root / name).write_text(_SHADOW_MODULE, encoding="utf-8")

    @staticmethod
    def _venv_python(venv_path: Path) -> Path:
        """Return the interpreter created inside a virtual environment."""
        candidates = (
            venv_path / "Scripts" / "python.exe",
            venv_path / "bin" / "python",
        )
        for candidate in candidates:
            if candidate.is_file():
                return candidate
        raise AssertionError(f"virtual environment has no interpreter: {venv_path}")

    def test_record_failure_tracks_deferred_failures(self):
        """record_failure should log and retain messages for later reporting."""
        runner = Runner()
        runner.logger = MagicMock()

        runner.record_failure("Robot failed with exit code 1")

        runner.logger.error.assert_called_once_with("Robot failed with exit code 1")
        self.assertTrue(runner.has_failures())
        self.assertEqual(runner.get_failures(), ["Robot failed with exit code 1"])

    def test_reset_failures_clears_deferred_failures(self):
        """reset_failures should clear previously recorded failures."""
        runner = Runner()
        runner.record_failure("Robot failed with exit code 1")

        runner.reset_failures()

        self.assertFalse(runner.has_failures())
        self.assertEqual(runner.get_failures(), [])
