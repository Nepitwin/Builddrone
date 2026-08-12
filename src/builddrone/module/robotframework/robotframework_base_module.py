"""Shared helpers for Robot Framework modules."""

from __future__ import annotations

from abc import ABC
from pathlib import Path

from builddrone.base_module import BaseModule
from builddrone.drone_exception import DroneException
from builddrone.runner import Runner


class RobotframeworkBaseModule(
    BaseModule, ABC
):  # pylint: disable=too-few-public-methods
    """Common behavior for Robot Framework command modules."""

    command_prefix: list[str] = []
    log_message: str = ""
    failure_label: str = ""

    def run(self, runner: Runner, args: dict) -> None:
        """Run a Robot Framework command with expanded CLI arguments."""
        runner.logger.info(self.log_message)
        exit_code = self._run_command(runner, args)

        if exit_code != 0:
            raise DroneException(
                f"{self.failure_label} failed with exit code {exit_code}"
            )

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
