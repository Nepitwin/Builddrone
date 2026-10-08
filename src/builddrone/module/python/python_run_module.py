"""Python run module."""

from __future__ import annotations

import os
from pathlib import Path

from builddrone.base_module import BaseModule
from builddrone.drone_exception import DroneException
from builddrone.path_safety import reject_symlink_component
from builddrone.runner import Runner


class PythonRunModule(BaseModule):  # pylint: disable=too-few-public-methods
    """A module responsible for running Python source files.

    Blueprint configuration arguments:
        "source": "Python file to execute"
    """

    def run(self, runner: Runner, args: dict) -> None:
        """Run a Python source file with the configured interpreter.

        Args:
            runner: Runner instance used to execute commands.
            args: Module configuration arguments.
        """
        runner.logger.info("Running...")
        source = args.get("source")

        if not isinstance(source, str) or not source:
            raise DroneException("No source provided for run")

        base_path = Path(runner.get_base_path())
        source_path = Path(source)
        if not os.path.isabs(source):
            source_path = base_path / source_path
        reject_symlink_component(source_path, base_path, "Source")

        exit_code = runner.run([source], cwd=str(base_path))

        if exit_code != 0:
            raise DroneException(f"Run failed with exit code {exit_code}")
