"""Tests for the Python install module."""

import unittest
from unittest.mock import MagicMock

from builddrone.drone_exception import DroneException
from builddrone.module.python.install_module import PythonInstallModule
from builddrone.runner import Runner


class TestPythonInstallModule(unittest.TestCase):
    """Verify install execution behavior."""

    def setUp(self):
        """Set up a mocked runner."""
        self.mock_runner = MagicMock(spec=Runner)
        self.mock_runner.logger = MagicMock()

    def test_run_installs_source(self):
        """Run pip install against the configured source."""
        self.mock_runner.run.return_value = 0

        module = PythonInstallModule()
        module.run(self.mock_runner, {"source": "build"})

        self.mock_runner.logger.info.assert_called_with("Installing...")
        self.mock_runner.run.assert_called_once_with(["-m", "pip", "install", "build"])

    def test_run_without_source_raises(self):
        """Reject missing install source."""
        module = PythonInstallModule()

        with self.assertRaises(DroneException) as context:
            module.run(self.mock_runner, {})

        self.assertEqual(str(context.exception), "No source provided for install")
        self.mock_runner.run.assert_not_called()

    def test_run_with_nonzero_exit_code_raises(self):
        """Raise when pip install returns a non-zero exit code."""
        self.mock_runner.run.return_value = 1

        module = PythonInstallModule()

        with self.assertRaises(DroneException) as context:
            module.run(self.mock_runner, {"source": "build"})

        self.assertEqual(str(context.exception), "Install failed with exit code 1")
