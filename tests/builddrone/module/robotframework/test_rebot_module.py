"""Tests for the Robot Framework rebot module."""

import unittest
from pathlib import Path
from unittest.mock import MagicMock

from builddrone.drone_exception import DroneException
from builddrone.module.robotframework.rebot_module import (
    RobotframeworkRebotModule,
)
from builddrone.runner import Runner


class TestRobotframeworkRebotModule(unittest.TestCase):
    """Verify rebot command expansion and execution."""

    def setUp(self):
        """Set up a mocked runner."""
        self.mock_runner = MagicMock(spec=Runner)
        self.mock_runner.logger = MagicMock()

    def test_run_builds_command_from_dictionary(self):
        """Convert a dictionary of arguments into a rebot command."""
        self.mock_runner.run.return_value = 0

        module = RobotframeworkRebotModule()
        cwd = Path("ROOT") / "atests"
        module.run(
            self.mock_runner,
            {
                "arguments": {
                    "--name": "ATests",
                    "--outputdir": "result",
                    "-x": "rebot_xunit.xml",
                    "result/uia2/output.xml": None,
                    "result/uia3/output.xml": None,
                },
                "cwd": cwd,
            },
        )

        self.mock_runner.logger.info.assert_called_with("Rebot...")
        self.mock_runner.run.assert_called_once_with(
            [
                "-m",
                "robot.rebot",
                "--name",
                "ATests",
                "--outputdir",
                "result",
                "-x",
                "rebot_xunit.xml",
                "result/uia2/output.xml",
                "result/uia3/output.xml",
            ],
            cwd=str(cwd),
        )

    def test_run_without_arguments_dictionary_raises(self):
        """Reject arguments that are not dictionaries."""
        module = RobotframeworkRebotModule()

        with self.assertRaises(DroneException) as context:
            module.run(self.mock_runner, {"arguments": []})

        self.assertEqual(str(context.exception), "Arguments must be a dictionary")
        self.mock_runner.run.assert_not_called()

    def test_run_with_invalid_cwd_raises(self):
        """Reject a cwd value that is not path-like."""
        module = RobotframeworkRebotModule()

        with self.assertRaises(DroneException) as context:
            module.run(
                self.mock_runner,
                {"arguments": {"--outputdir": "result"}, "cwd": 123},
            )

        self.assertEqual(str(context.exception), "Cwd must be a path or string")
        self.mock_runner.run.assert_not_called()

    def test_run_with_nonzero_exit_code_raises(self):
        """Raise when rebot returns a non-zero exit code."""
        self.mock_runner.run.return_value = 1

        module = RobotframeworkRebotModule()

        with self.assertRaises(DroneException) as context:
            module.run(
                self.mock_runner,
                {
                    "arguments": {"--outputdir": "result", "result/output.xml": None},
                    "cwd": "ROOT/atests",
                },
            )

        self.assertEqual(str(context.exception), "Rebot failed with exit code 1")
