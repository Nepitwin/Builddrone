"""Tests for the Robot Framework rebot module."""

# These tests intentionally mirror the robot module's contract.
# pylint: disable=duplicate-code

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
        self.base_path = Path("blueprint")
        self.mock_runner.get_base_path.return_value = self.base_path

    def test_run_builds_command_from_key_value_and_standalone_arguments(self):
        """Convert mixed argument entries into a rebot command."""
        self.mock_runner.run.return_value = 0

        module = RobotframeworkRebotModule()
        cwd = Path("ROOT") / "atests"
        module.run(
            self.mock_runner,
            {
                "arguments": [
                    {"--name": "ATests"},
                    {"--outputdir": "result"},
                    {"-x": "rebot_xunit.xml"},
                    "result/uia2/output.xml",
                    "result/uia3/output.xml",
                ],
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
            cwd=str(self.base_path / cwd),
        )

    def test_run_without_cwd_uses_runner_base_path(self):
        """Use the blueprint directory when cwd is omitted."""
        self.mock_runner.run.return_value = 0

        RobotframeworkRebotModule().run(self.mock_runner, {"arguments": []})

        self.mock_runner.run.assert_called_once_with(
            ["-m", "robot.rebot"], cwd=str(self.base_path)
        )

    def test_run_without_arguments_list_raises(self):
        """Reject arguments that are not lists."""
        module = RobotframeworkRebotModule()

        with self.assertRaises(DroneException) as context:
            module.run(self.mock_runner, {"arguments": {}})

        self.assertEqual(str(context.exception), "Arguments must be a list")
        self.mock_runner.run.assert_not_called()

    def test_run_with_invalid_cwd_raises(self):
        """Reject a cwd value that is not path-like."""
        module = RobotframeworkRebotModule()

        with self.assertRaises(DroneException) as context:
            module.run(
                self.mock_runner,
                {"arguments": [{"--outputdir": "result"}], "cwd": 123},
            )

        self.assertEqual(str(context.exception), "Cwd must be a path or string")
        self.mock_runner.run.assert_not_called()

    def test_run_defers_test_failure_exit_codes(self):
        """Log and continue when rebot reports failed tests (exit codes 1-250)."""
        module = RobotframeworkRebotModule()
        args = {
            "arguments": [{"--outputdir": "result"}, "result/output.xml"],
            "cwd": "ROOT/atests",
        }

        for exit_code in (1, 249, 250):
            with self.subTest(exit_code=exit_code):
                self.mock_runner.run.return_value = exit_code
                self.mock_runner.record_failure.reset_mock()

                module.run(self.mock_runner, args)

                self.mock_runner.record_failure.assert_called_once_with(
                    f"Rebot failed with exit code {exit_code}"
                )

    def test_run_raises_on_tool_error_exit_codes(self):
        """Stop immediately on help, invalid data, interrupt, and internal errors."""
        module = RobotframeworkRebotModule()
        args = {
            "arguments": [{"--outputdir": "result"}, "result/output.xml"],
            "cwd": "ROOT/atests",
        }

        for exit_code in (251, 252, 253, 255):
            with self.subTest(exit_code=exit_code):
                self.mock_runner.run.return_value = exit_code
                self.mock_runner.record_failure.reset_mock()

                with self.assertRaises(DroneException) as context:
                    module.run(self.mock_runner, args)

                self.assertEqual(
                    str(context.exception),
                    f"Rebot failed with exit code {exit_code}",
                )
                self.mock_runner.record_failure.assert_not_called()
