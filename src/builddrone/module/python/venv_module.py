"""Python virtual environment module."""

from pathlib import Path

from builddrone.base_module import BaseModule
from builddrone.drone_exception import DroneException
from builddrone.runner import Runner


class PythonVirtualEnvironmentModule(
    BaseModule
):  # pylint: disable=too-few-public-methods
    """A module responsible for configuring a Python virtual environment.

    Blueprint configuration arguments:
        "source": "Virtual environment root path to use; empty string resets the runner"
    """

    def run(self, runner: Runner, args: dict) -> None:
        """Configure the runner to use a virtual environment interpreter."""
        source = args.get("source")

        if source == "":
            runner.logger.info("Resetting runner to the current Python interpreter...")
            runner.reset_runner()
            return

        if not isinstance(source, str) or not source:
            raise DroneException("No source provided for virtual environment")

        venv_path = Path(source)
        if not venv_path.is_absolute():
            venv_path = Path(runner.get_base_path()) / venv_path

        python_executable = self._resolve_python_executable(venv_path)

        if python_executable is None:
            raise DroneException(f"Invalid virtual environment path: {venv_path}")

        runner.logger.info("Using virtual environment: %s", venv_path)
        runner.set_runner(str(python_executable))

    @staticmethod
    def _resolve_python_executable(venv_path: Path) -> Path | None:
        """Resolve the interpreter path inside the virtual environment."""
        candidate_paths = (
            venv_path / "Scripts" / "python.exe",
            venv_path / "bin" / "python",
        )

        for candidate in candidate_paths:
            if candidate.is_file():
                return candidate

        return None
