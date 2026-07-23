"""Tests for the Python virtual environment module."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from builddrone.drone_exception import DroneException
from builddrone.module.python.venv_module import PythonVirtualEnvironmentModule
from builddrone.runner import Runner


class TestPythonVirtualEnvironmentModule(unittest.TestCase):
    """Verify venv configuration behavior."""

    def setUp(self):
        """Set up a mocked runner."""
        self.mock_runner = MagicMock(spec=Runner)
        self.mock_runner.logger = MagicMock()
        self.mock_runner.get_base_path.return_value = Path.cwd()

    def test_run_sets_runner_from_venv_root(self):
        """Resolve the interpreter from a .venv-style root path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            venv_root = Path(temp_dir) / ".venv"
            python_executable = venv_root / "Scripts" / "python.exe"
            python_executable.parent.mkdir(parents=True)
            python_executable.write_text("", encoding="utf-8")

            module = PythonVirtualEnvironmentModule()
            module.run(self.mock_runner, {"source": str(venv_root)})

        self.mock_runner.logger.info.assert_called_with(
            "Using virtual environment: %s", venv_root
        )
        self.mock_runner.set_runner.assert_called_once_with(str(python_executable))
        self.mock_runner.reset_runner.assert_not_called()

    def test_run_resolves_relative_source_from_runner_base_path(self):
        """Resolve a relative environment from the blueprint directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            python_executable = base_path / ".venv" / "bin" / "python"
            python_executable.parent.mkdir(parents=True)
            python_executable.write_text("", encoding="utf-8")
            self.mock_runner.get_base_path.return_value = base_path

            module = PythonVirtualEnvironmentModule()
            module.run(self.mock_runner, {"source": ".venv"})

        self.mock_runner.get_base_path.assert_called_once_with()
        self.mock_runner.set_runner.assert_called_once_with(str(python_executable))

    def test_run_empty_source_resets_runner(self):
        """Reset the runner when source is an empty string."""
        module = PythonVirtualEnvironmentModule()

        module.run(self.mock_runner, {"source": ""})

        self.mock_runner.logger.info.assert_called_with(
            "Resetting runner to the current Python interpreter..."
        )
        self.mock_runner.reset_runner.assert_called_once_with()
        self.mock_runner.set_runner.assert_not_called()

    def test_run_without_source_raises(self):
        """Reject a missing virtual environment source."""
        module = PythonVirtualEnvironmentModule()

        with self.assertRaises(DroneException) as context:
            module.run(self.mock_runner, {})

        self.assertEqual(
            str(context.exception), "No source provided for virtual environment"
        )

    @patch("builddrone.module.python.venv_module.venv.create")
    def test_run_creates_missing_venv(self, create_venv):
        """Create and use a virtual environment when it does not exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            venv_root = Path(temp_dir) / ".venv"
            python_executable = venv_root / "bin" / "python"

            def create_environment(path, with_pip):
                self.assertEqual(path, venv_root)
                self.assertTrue(with_pip)
                python_executable.parent.mkdir(parents=True)
                python_executable.write_text("", encoding="utf-8")

            create_venv.side_effect = create_environment

            module = PythonVirtualEnvironmentModule()
            module.run(self.mock_runner, {"source": str(venv_root)})

        create_venv.assert_called_once_with(venv_root, with_pip=True)
        self.mock_runner.set_runner.assert_called_once_with(str(python_executable))

    @patch("builddrone.module.python.venv_module.venv.create")
    def test_run_with_invalid_venv_path_raises(self, create_venv):
        """Reject a path when virtual environment creation fails."""
        create_venv.side_effect = OSError("permission denied")
        module = PythonVirtualEnvironmentModule()

        with self.assertRaises(DroneException) as context:
            module.run(self.mock_runner, {"source": "missing/.venv"})

        self.assertEqual(
            str(context.exception),
            f"Could not create virtual environment: {Path.cwd() / 'missing/.venv'}",
        )
