"""Runner module for executing build commands."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

from builddrone.drone_exception import DroneException

_LOG_FORMAT = "%(levelname)s:%(name)s:%(message)s"


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
        """
        full_cmd = [self._python_path] + cmd
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
