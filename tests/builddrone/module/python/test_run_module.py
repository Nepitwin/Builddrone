"""Tests for the Python run module."""

import unittest
from unittest.mock import MagicMock

from builddrone.drone_exception import DroneException
from builddrone.module.python.run_module import PythonRunModule
from builddrone.runner import Runner


class TestPythonRunModule(unittest.TestCase):
    """Verify run execution behavior."""

    def setUp(self):
        """Set up a mocked runner."""
        self.mock_runner = MagicMock(spec=Runner)
        self.mock_runner.logger = MagicMock()

    def test_run_executes_source(self):
        """Run a Python source file."""
        self.mock_runner.run.return_value = 0

        module = PythonRunModule()
        module.run(self.mock_runner, {"source": "src/app.py"})

        self.mock_runner.logger.info.assert_called_with("Running...")
        self.mock_runner.run.assert_called_once_with(["src/app.py"])

    def test_run_without_source_raises(self):
        """Reject missing source file."""
        module = PythonRunModule()

        with self.assertRaises(DroneException) as context:
            module.run(self.mock_runner, {})

        self.assertEqual(str(context.exception), "No source provided for run")
        self.mock_runner.run.assert_not_called()

    def test_run_with_nonzero_exit_code_raises(self):
        """Raise when the Python file execution fails."""
        self.mock_runner.run.return_value = 2

        module = PythonRunModule()

        with self.assertRaises(DroneException) as context:
            module.run(self.mock_runner, {"source": "src/app.py"})

        self.assertEqual(str(context.exception), "Run failed with exit code 2")
