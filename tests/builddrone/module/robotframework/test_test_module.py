"""Tests for the Robot Framework test module."""

import unittest
from pathlib import Path
from unittest.mock import MagicMock

from builddrone.drone_exception import DroneException
from builddrone.module.robotframework.test_module import RobotframeworkTestModule
from builddrone.runner import Runner


class TestRobotframeworkTestModule(unittest.TestCase):
    """Verify robot command expansion and execution."""

    def setUp(self):
        """Set up a mocked runner."""
        self.mock_runner = MagicMock(spec=Runner)
        self.mock_runner.logger = MagicMock()
        self.base_path = Path("blueprint")
        self.mock_runner.get_base_path.return_value = self.base_path

    def test_run_builds_command_from_dictionary(self):
        """Convert a dictionary of arguments into a robot command."""
        self.mock_runner.run.return_value = 0

        module = RobotframeworkTestModule()
        cwd = Path("ROOT") / "atests"
        module.run(
            self.mock_runner,
            {
                "arguments": {
                    "--name": "UIA2",
                    "--variable": "UIA:UIA2",
                    "--outputdir": "../result/uia2",
                    ".": None,
                },
                "cwd": cwd,
            },
        )

        self.mock_runner.logger.info.assert_called_with("Robot...")
        self.mock_runner.run.assert_called_once_with(
            [
                "-m",
                "robot",
                "--name",
                "UIA2",
                "--variable",
                "UIA:UIA2",
                "--outputdir",
                "../result/uia2",
                ".",
            ],
            cwd=str(self.base_path / cwd),
        )

    def test_run_without_cwd_uses_runner_base_path(self):
        """Use the blueprint directory when cwd is omitted."""
        self.mock_runner.run.return_value = 0

        RobotframeworkTestModule().run(self.mock_runner, {"arguments": {}})

        self.mock_runner.run.assert_called_once_with(
            ["-m", "robot"], cwd=str(self.base_path)
        )

    def test_run_without_arguments_dictionary_raises(self):
        """Reject arguments that are not dictionaries."""
        module = RobotframeworkTestModule()

        with self.assertRaises(DroneException) as context:
            module.run(self.mock_runner, {"arguments": []})

        self.assertEqual(str(context.exception), "Arguments must be a dictionary")
        self.mock_runner.run.assert_not_called()

    def test_run_with_invalid_cwd_raises(self):
        """Reject a cwd value that is not path-like."""
        module = RobotframeworkTestModule()

        with self.assertRaises(DroneException) as context:
            module.run(self.mock_runner, {"arguments": {"--name": "UIA2"}, "cwd": 123})

        self.assertEqual(str(context.exception), "Cwd must be a path or string")
        self.mock_runner.run.assert_not_called()

    def test_run_with_nonzero_exit_code_raises(self):
        """Raise when robot returns a non-zero exit code."""
        self.mock_runner.run.return_value = 1

        module = RobotframeworkTestModule()

        with self.assertRaises(DroneException) as context:
            module.run(
                self.mock_runner,
                {
                    "arguments": {"--outputdir": "../result/uia2", ".": None},
                    "cwd": "ROOT/atests",
                },
            )

        self.assertEqual(str(context.exception), "Robot failed with exit code 1")
