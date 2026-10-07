"""Runner module for executing build commands."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

from builddrone.drone_exception import DroneException

_LOG_FORMAT = "%(levelname)s:%(name)s:%(message)s"
_SAFE_PATH_VERSION = (3, 11)

# Python 3.8–3.10 have no -P. -S skips the startup site import so a workspace
# site.py cannot run before the working directory is removed from sys.path.
# site.main() then adds site-packages, including a virtual environment, and
# the user site. -I would also hide the working directory, but it disables
# the user site.
_SAFE_MODULE_LAUNCHER = r"""
import sys

_NT = "nt" in sys.builtin_module_names
if _NT:
    import nt as _plat
else:
    import posix as _plat

_cwd = _plat.getcwd()


def _is_abs(path):
    if _NT:
        if path.startswith("\\\\") or path.startswith("//"):
            return True
        return len(path) >= 3 and path[1] == ":" and path[2] in "\\/"
    return path.startswith("/")


def _key(path):
    if path in ("", "."):
        path = _cwd
    elif not _is_abs(path):
        sep = "\\" if _NT else "/"
        path = _cwd.rstrip("/\\") + sep + path
    if _NT:
        pieces = path.replace("/", "\\").split("\\")
    else:
        pieces = path.split("/")
    stack = []
    for piece in pieces:
        if piece in ("", "."):
            continue
        if piece == ".." and stack:
            stack.pop()
            continue
        stack.append(piece)
    if _NT:
        if path.startswith("\\\\") or path.startswith("//"):
            normalized = "\\\\" + "\\".join(stack)
        else:
            normalized = "\\".join(stack)
        return normalized.casefold()
    return "/" + "/".join(stack)


_cwd_key = _key(_cwd)
sys.path[:] = [entry for entry in sys.path if _key(entry) != _cwd_key]

import os

_real_cwd = os.path.normcase(os.path.realpath(_cwd))


def _is_cwd_entry(entry):
    if _key(entry) == _cwd_key:
        return True
    try:
        candidate = entry or _cwd
        return os.path.normcase(os.path.realpath(candidate)) == _real_cwd
    except (OSError, ValueError):
        return False


sys.path[:] = [entry for entry in sys.path if not _is_cwd_entry(entry)]

import site

site.main()
import runpy

module = sys.argv[1]
sys.argv = sys.argv[1:]
runpy.run_module(module, run_name="__main__", alter_sys=True)
"""


def _python_command(
    python_path: str, cmd: list[str], version: tuple[int, ...]
) -> list[str]:
    """Build a command that does not import a workspace module by name.

    ``python -m`` prepends the working directory to ``sys.path``. Python 3.11
    and newer skip that entry with ``-P``. Earlier releases drop the empty
    string and working-directory entries, then call ``runpy.run_module``.
    """
    if len(cmd) < 2 or cmd[0] != "-m":
        return [python_path, *cmd]
    if version >= _SAFE_PATH_VERSION:
        return [python_path, "-P", *cmd]
    return [python_path, "-S", "-c", _SAFE_MODULE_LAUNCHER, *cmd[1:]]


def configure_logging() -> None:
    """Configure builddrone logging for CI-friendly stdout output."""
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stdout,
        format=_LOG_FORMAT,
    )


class Runner:
    """Execute build commands using a configured Python interpreter."""

    def __init__(self):
        """Initialize the runner."""
        configure_logging()
        self.logger = logging.getLogger(__name__)

        self._python_path = sys.executable
        self._base_path: Path | None = None
        self._failures: list[str] = []
        if not self._python_path:
            raise DroneException("Python executable not found")

    def set_runner(self, python_path):
        """Set the Python executable used for command execution."""
        if os.path.exists(python_path) and os.path.isfile(python_path):
            self._python_path = python_path

    def reset_runner(self):
        """Reset the runner to use the current Python interpreter."""
        self._python_path = sys.executable
        if not self._python_path:
            raise DroneException("Python executable not found")

    def set_base_path(self, base_path: str | Path | None) -> None:
        """Set the base directory used for relative paths."""
        self._base_path = None if base_path is None else Path(base_path)

    def get_base_path(self) -> Path:
        """Return the base directory used for relative paths."""
        return self._base_path or Path.cwd()

    def run(self, cmd, cwd=None) -> int:
        """Execute a Python command and return the exit code.

        Child stderr is merged into stdout so PowerShell/AppVeyor do not treat
        informational tool output (for example pip version notices) as errors.

        Module commands do not put the working directory on ``sys.path``.
        Otherwise a workspace ``pip.py``, ``build.py``, ``pylint.py``,
        ``twine.py``, or ``robot.py`` would run instead of the installed tool
        and could read CI tokens from the environment.
        """
        full_cmd = _python_command(self._python_path, list(cmd), sys.version_info)
        result = subprocess.run(
            full_cmd,
            cwd=cwd,
            check=False,
            stderr=subprocess.STDOUT,
        )
        return result.returncode

    def reset_failures(self) -> None:
        """Clear recorded deferred failures."""
        self._failures.clear()

    def record_failure(self, message: str) -> None:
        """Record a deferred failure to report after the current stage finishes."""
        self._failures.append(message)
        self.logger.error(message)

    def has_failures(self) -> bool:
        """Return whether any deferred failures were recorded."""
        return bool(self._failures)

    def get_failures(self) -> list[str]:
        """Return recorded deferred failure messages."""
        return list(self._failures)
