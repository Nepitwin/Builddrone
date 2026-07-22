"""Tests for the Python build module."""

import unittest
from pathlib import Path
from unittest.mock import MagicMock

from builddrone.drone_exception import DroneException
from builddrone.module.python.build_module import PythonBuildModule
from builddrone.runner import Runner


class TestPythonBuildModule(unittest.TestCase):
    """Verify build execution behavior."""

    def setUp(self):
        """Set up a mocked runner."""
        self.mock_runner = MagicMock(spec=Runner)
        self.mock_runner.logger = MagicMock()
        self.mock_runner.get_base_path.return_value = Path("blueprint")

    def test_run_builds_without_arguments(self):
        """Run build with no command arguments."""
        self.mock_runner.run.return_value = 0

        module = PythonBuildModule()
        module.run(self.mock_runner, {})

        self.mock_runner.logger.info.assert_called_with("Building...")
        self.mock_runner.run.assert_called_once_with(
            ["-m", "build"], cwd=str(Path("blueprint"))
        )

    def test_run_ignores_provided_args(self):
        """Run build without passing args to the command."""
        self.mock_runner.run.return_value = 0

        module = PythonBuildModule()
        module.run(self.mock_runner, {"ignored": True})

        self.mock_runner.run.assert_called_once_with(
            ["-m", "build"], cwd=str(Path("blueprint"))
        )

    def test_run_with_nonzero_exit_code_raises(self):
        """Raise when build returns a non-zero exit code."""
        self.mock_runner.run.return_value = 1

        module = PythonBuildModule()

        with self.assertRaises(DroneException) as context:
            module.run(self.mock_runner, {})

        self.assertEqual(str(context.exception), "Build failed with exit code 1")
