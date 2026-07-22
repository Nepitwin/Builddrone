"""Shared helpers for Robot Framework modules."""

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
        arguments = args.get("arguments", {})
        cwd = args.get("cwd")

        if not isinstance(arguments, dict):
            raise DroneException("Arguments must be a dictionary")

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
        exit_code = runner.run(command, cwd=str(working_directory))

        if exit_code != 0:
            raise DroneException(
                f"{self.failure_label} failed with exit code {exit_code}"
            )

    def _build_command(self, arguments: dict) -> list[str]:
        """Convert a dictionary of CLI options into a Robot Framework command."""
        command: list[str] = list(self.command_prefix)

        for key, value in arguments.items():
            if isinstance(value, bool):
                if value:
                    command.append(str(key))
                continue

            if isinstance(value, (list, tuple)):
                command.append(str(key))
                command.extend(str(item) for item in value)
                continue

            if value is None:
                command.append(str(key))
                continue

            command.extend([str(key), str(value)])

        return command
