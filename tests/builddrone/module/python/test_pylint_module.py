"""Tests for the Python pylint module."""

import unittest
from pathlib import Path
from unittest.mock import MagicMock

from builddrone.drone_exception import DroneException
from builddrone.module.python.pylint_module import PylintModule
from builddrone.runner import Runner


class TestPylintModule(unittest.TestCase):
    """Verify pylint execution behavior."""

    def setUp(self):
        """Set up a mocked runner."""
        self.mock_runner = MagicMock(spec=Runner)
        self.mock_runner.logger = MagicMock()
        self.mock_runner.get_base_path.return_value = Path("blueprint")

    def test_run_with_paths(self):
        """Run pylint against the configured paths."""
        self.mock_runner.run.return_value = 0

        module = PylintModule()
        module.run(self.mock_runner, {"paths": ["src/builddrone", "tests"]})

        self.mock_runner.logger.info.assert_called_with("Pylint...")
        self.mock_runner.run.assert_called_once_with(
            ["-m", "pylint", "src/builddrone", "tests"],
            cwd=str(Path("blueprint")),
        )

    def test_run_without_targets_raises(self):
        """Reject missing pylint paths and files."""
        module = PylintModule()

        with self.assertRaises(DroneException) as context:
            module.run(self.mock_runner, {})

        self.assertEqual(
            str(context.exception), "No paths or files provided for pylint"
        )
        self.mock_runner.run.assert_not_called()

    def test_run_with_files(self):
        """Run pylint against explicitly configured Python files."""
        self.mock_runner.run.return_value = 0

        module = PylintModule()
        module.run(self.mock_runner, {"files": ["main.py", "tools/check.py"]})

        self.mock_runner.run.assert_called_once_with(
            ["-m", "pylint", "main.py", "tools/check.py"],
            cwd=str(Path("blueprint")),
        )

    def test_run_with_invalid_files_raises(self):
        """Reject files that are not provided as a list of names."""
        module = PylintModule()

        with self.assertRaises(DroneException) as context:
            module.run(self.mock_runner, {"files": "main.py"})

        self.assertEqual(
            str(context.exception), "Files must be a list of non-empty strings"
        )
        self.mock_runner.run.assert_not_called()

    def test_run_with_ignored_names(self):
        """Pass ignored file and directory names to pylint."""
        self.mock_runner.run.return_value = 0

        module = PylintModule()
        module.run(
            self.mock_runner,
            {"paths": ["."], "ignore": [".venv", "build"]},
        )

        self.mock_runner.run.assert_called_once_with(
            ["-m", "pylint", "--ignore", ".venv,build", "."],
            cwd=str(Path("blueprint")),
        )

    def test_run_with_invalid_ignore_raises(self):
        """Reject ignore values that are not lists of names."""
        module = PylintModule()

        with self.assertRaises(DroneException) as context:
            module.run(self.mock_runner, {"paths": ["."], "ignore": ".venv"})

        self.assertEqual(
            str(context.exception), "Ignore must be a list of non-empty strings"
        )
        self.mock_runner.run.assert_not_called()

    def test_run_with_nonzero_exit_code_raises(self):
        """Raise when pylint returns a non-zero exit code."""
        self.mock_runner.run.return_value = 8

        module = PylintModule()

        with self.assertRaises(DroneException) as context:
            module.run(self.mock_runner, {"paths": ["src/builddrone"]})

        self.assertEqual(str(context.exception), "Pylint failed with exit code 8")
