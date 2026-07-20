"""Tests for the Python pylint module."""

import unittest
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

    def test_run_with_paths(self):
        """Run pylint against the configured paths."""
        self.mock_runner.run.return_value = 0

        module = PylintModule()
        module.run(self.mock_runner, {"paths": ["src/builddrone", "tests"]})

        self.mock_runner.logger.info.assert_called_with("Pylint...")
        self.mock_runner.run.assert_called_once_with(
            ["-m", "pylint", "src/builddrone", "tests"]
        )

    def test_run_without_paths_raises(self):
        """Reject missing pylint paths."""
        module = PylintModule()

        with self.assertRaises(DroneException) as context:
            module.run(self.mock_runner, {})

        self.assertEqual(str(context.exception), "No paths provided for pylint")
        self.mock_runner.run.assert_not_called()

    def test_run_with_nonzero_exit_code_raises(self):
        """Raise when pylint returns a non-zero exit code."""
        self.mock_runner.run.return_value = 8

        module = PylintModule()

        with self.assertRaises(DroneException) as context:
            module.run(self.mock_runner, {"paths": ["src/builddrone"]})

        self.assertEqual(str(context.exception), "Pylint failed with exit code 8")
