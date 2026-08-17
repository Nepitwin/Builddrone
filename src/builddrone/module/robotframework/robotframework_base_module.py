"""Shared helpers for Robot Framework modules."""

from __future__ import annotations

from abc import ABC
from pathlib import Path

from builddrone.base_module import BaseModule
from builddrone.drone_exception import DroneException
from builddrone.runner import Runner

# Robot and Rebot return 1-249 for the number of failed tests and 250 when
# 250 or more tests failed. Those are result codes, not tool errors.
_TEST_FAILURE_EXIT_CODE_MIN = 1
_TEST_FAILURE_EXIT_CODE_MAX = 250


class RobotframeworkBaseModule(
    BaseModule, ABC
):  # pylint: disable=too-few-public-methods
    """Common behavior for Robot Framework command modules."""

    command_prefix: list[str] = []
    log_message: str = ""
    failure_label: str = ""

    def run(self, runner: Runner, args: dict) -> None:
        """Run a Robot Framework command with expanded CLI arguments.

        Exit codes 1-250 mean tests failed. Those are logged and deferred so
        later steps in the same stage still run. All other non-zero codes stop
        the stage immediately.
        """
        runner.logger.info(self.log_message)
        exit_code = self._run_command(runner, args)

        if exit_code == 0:
            return

        message = f"{self.failure_label} failed with exit code {exit_code}"
        if self._is_test_failure_exit_code(exit_code):
            runner.record_failure(message)
            return

        raise DroneException(message)

    @staticmethod
    def _is_test_failure_exit_code(exit_code: int) -> bool:
        """Return whether the exit code reports failed tests, not a tool error."""
        return _TEST_FAILURE_EXIT_CODE_MIN <= exit_code <= _TEST_FAILURE_EXIT_CODE_MAX

    def _run_command(self, runner: Runner, args: dict) -> int:
        """Run a Robot Framework command and return its exit code."""
        arguments = args.get("arguments", [])
        cwd = args.get("cwd")

        if not isinstance(arguments, list):
            raise DroneException("Arguments must be a list")

        if cwd is not None and not isinstance(cwd, (str, Path)):
            raise DroneException("Cwd must be a path or string")

        working_directory = Path(runner.get_base_path())
        if cwd is not None:
            configured_cwd = Path(cwd)
            working_directory = (
                configured_cwd
                if configured_cwd.is_absolute()
                else working_directory / configured_cwd
            )

        command = self._build_command(arguments)
        return runner.run(command, cwd=str(working_directory))

    def _build_command(self, arguments: list) -> list[str]:
        """Convert standalone and key/value arguments into a command."""
        command: list[str] = list(self.command_prefix)

        for argument in arguments:
            if isinstance(argument, str):
                command.append(argument)
                continue

            if not isinstance(argument, dict) or len(argument) != 1:
                raise DroneException(
                    "Each argument must be a string or a single key/value pair"
                )

            key, value = next(iter(argument.items()))
            if isinstance(value, bool):
                if value:
                    command.append(str(key))
                continue

            if isinstance(value, (list, tuple)):
                command.append(str(key))
                command.extend(str(item) for item in value)
                continue

            if value is None:
                raise DroneException("Argument values must not be null")

            command.extend([str(key), str(value)])

        return command
