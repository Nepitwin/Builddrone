"""Python build module."""

from __future__ import annotations

import os
from pathlib import Path

from builddrone.base_module import BaseModule
from builddrone.drone_exception import DroneException
from builddrone.path_safety import reject_symlink_component
from builddrone.runner import Runner

# These directories are not package inputs. Virtual environments are recreated
# beside the project and may contain symlinks such as lib64; VCS metadata and
# bytecode caches are not copied into the sdist or wheel.
_UNPACKAGED_DIRECTORIES = frozenset(
    {
        ".bzr",
        ".git",
        ".hg",
        ".svn",
        ".venv",
        "__pycache__",
        "_darcs",
        "venv",
    }
)


class PythonBuildModule(BaseModule):  # pylint: disable=too-few-public-methods
    """A module responsible for building the project.

    Blueprint configuration arguments:
        None
    """

    def run(self, runner: Runner, _args: dict) -> None:
        """Build the project with ``python -m build``.

        Fails before the builder runs when a packaged path contains a symlink.
        A regular archive is not treated as proof that its members are safe,
        because setuptools copies symlink targets in as normal file bytes.

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
            kept_directories: list[str] = []
            for dir_name in dir_names:
                directory = Path(root) / dir_name
                if dir_name in _UNPACKAGED_DIRECTORIES and not directory.is_symlink():
                    continue
                reject_symlink_component(directory, base_path, "Packaged path")
                kept_directories.append(dir_name)
            dir_names[:] = kept_directories
            for file_name in file_names:
                reject_symlink_component(
                    Path(root) / file_name, base_path, "Packaged path"
                )
