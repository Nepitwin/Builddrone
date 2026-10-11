"""Python build module."""

from __future__ import annotations

import os
from pathlib import Path

from builddrone.base_module import BaseModule
from builddrone.drone_exception import DroneException
from builddrone.path_safety import reject_symlink_component
from builddrone.runner import Runner


class PythonBuildModule(BaseModule):  # pylint: disable=too-few-public-methods
    """A module responsible for building the project.

    Blueprint configuration arguments:
        None
    """

    def run(self, runner: Runner, _args: dict) -> None:
        """Build the project with ``python -m build``.

        Fails before the builder runs when any path under the workspace contains
        a symlink, including directories such as ``venv`` and ``.git``. A
        manifest can still package those names, and setuptools copies a symlink
        target in as normal file bytes.

        Args:
            runner: Runner instance used to execute commands.
            _args: Module configuration arguments. Unused.
        """
        runner.logger.info("Building...")
        base_path = Path(runner.get_base_path())
        self._reject_packaged_symlinks(base_path)
        exit_code = runner.run(["-m", "build"], cwd=str(base_path))

        if exit_code != 0:
            raise DroneException(f"Build failed with exit code {exit_code}")

    @staticmethod
    def _reject_packaged_symlinks(base_path: Path) -> None:
        for root, dir_names, file_names in os.walk(base_path, followlinks=False):
            for dir_name in dir_names:
                reject_symlink_component(
                    Path(root) / dir_name, base_path, "Packaged path"
                )
            for file_name in file_names:
                reject_symlink_component(
                    Path(root) / file_name, base_path, "Packaged path"
                )
