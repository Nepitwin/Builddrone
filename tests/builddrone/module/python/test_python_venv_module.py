"""Tests for the Python virtual environment module."""

# These tests share symlink setup patterns with other python modules.
# pylint: disable=duplicate-code

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from builddrone.drone_exception import DroneException
from builddrone.module.python.python_venv_module import PythonVirtualEnvironmentModule
from builddrone.runner import Runner


class TestPythonVirtualEnvironmentModule(unittest.TestCase):
    """Verify venv configuration behavior."""

    def setUp(self):
        """Set up a mocked runner."""
        self.mock_runner = MagicMock(spec=Runner)
        self.mock_runner.logger = MagicMock()
        self.mock_runner.get_base_path.return_value = Path.cwd()

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

    @patch("builddrone.module.python.python_venv_module.venv.create")
    def test_run_creates_fresh_venv(self, create_venv):
        """Always create a virtual environment instead of reusing a pre-seeded one."""
        with tempfile.TemporaryDirectory() as temp_dir:
            venv_root = Path(temp_dir) / ".venv"
            python_executable = venv_root / "bin" / "python"
            python_executable.parent.mkdir(parents=True)
            python_executable.write_text("planted", encoding="utf-8")

            def create_environment(path, with_pip, clear, symlinks):
                self.assertEqual(path, venv_root)
                self.assertTrue(with_pip)
                self.assertTrue(clear)
                self.assertFalse(symlinks)
                python_executable.write_text("fresh", encoding="utf-8")

            create_venv.side_effect = create_environment

            module = PythonVirtualEnvironmentModule()
            module.run(self.mock_runner, {"source": str(venv_root)})

        create_venv.assert_called_once_with(
            venv_root, with_pip=True, clear=True, symlinks=False
        )
        self.mock_runner.logger.info.assert_any_call(
            "Creating virtual environment: %s", venv_root
        )
        self.mock_runner.logger.info.assert_any_call(
            "Using virtual environment: %s", venv_root
        )
        self.mock_runner.set_runner.assert_called_once_with(str(python_executable))
        self.mock_runner.reset_runner.assert_not_called()

    @patch("builddrone.module.python.python_venv_module.venv.create")
    def test_run_resolves_relative_source_from_runner_base_path(self, create_venv):
        """Resolve a relative environment from the blueprint directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            python_executable = base_path / ".venv" / "bin" / "python"
            self.mock_runner.get_base_path.return_value = base_path

            def create_environment(_path, **_kwargs):
                python_executable.parent.mkdir(parents=True)
                python_executable.write_text("", encoding="utf-8")

            create_venv.side_effect = create_environment

            module = PythonVirtualEnvironmentModule()
            module.run(self.mock_runner, {"source": ".venv"})

        create_venv.assert_called_once_with(
            base_path / ".venv", with_pip=True, clear=True, symlinks=False
        )
        self.mock_runner.get_base_path.assert_called()
        self.mock_runner.set_runner.assert_called_once_with(str(python_executable))

    @patch("builddrone.module.python.python_venv_module.venv.create")
    def test_run_sets_runner_from_windows_venv_root(self, create_venv):
        """Resolve the interpreter from a Windows-style venv root."""
        with tempfile.TemporaryDirectory() as temp_dir:
            venv_root = Path(temp_dir) / ".venv"
            python_executable = venv_root / "Scripts" / "python.exe"

            def create_environment(_path, **_kwargs):
                python_executable.parent.mkdir(parents=True)
                python_executable.write_text("", encoding="utf-8")

            create_venv.side_effect = create_environment

            module = PythonVirtualEnvironmentModule()
            module.run(self.mock_runner, {"source": str(venv_root)})

        self.mock_runner.set_runner.assert_called_once_with(str(python_executable))

    @patch("builddrone.module.python.python_venv_module.venv.create")
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

    @patch("builddrone.module.python.python_venv_module.venv.create")
    def test_run_rejects_missing_interpreter_after_create(self, create_venv):
        """Reject a path when creation succeeds but no interpreter is found."""
        with tempfile.TemporaryDirectory() as temp_dir:
            venv_root = Path(temp_dir) / ".venv"

            module = PythonVirtualEnvironmentModule()
            with self.assertRaises(DroneException) as context:
                module.run(self.mock_runner, {"source": str(venv_root)})

        create_venv.assert_called_once_with(
            venv_root, with_pip=True, clear=True, symlinks=False
        )
        self.assertEqual(
            str(context.exception),
            f"Invalid virtual environment path: {venv_root}",
        )
        self.mock_runner.set_runner.assert_not_called()

    def test_run_rejects_symlinked_venv_path(self):
        """Reject a virtual environment root that is a symlink."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            self.mock_runner.get_base_path.return_value = base_path
            host_dir = base_path / "host"
            host_dir.mkdir()
            link_path = base_path / ".venv"
            try:
                os.symlink(host_dir, link_path, target_is_directory=True)
            except OSError:
                self.skipTest("Cannot create directory symlinks on this platform")

            module = PythonVirtualEnvironmentModule()
            with self.assertRaises(DroneException) as context:
                module.run(self.mock_runner, {"source": ".venv"})

        self.assertEqual(
            str(context.exception),
            f"Virtual environment must not be a symlink: {link_path}",
        )
        self.mock_runner.set_runner.assert_not_called()

    def test_run_rejects_symlinked_venv_path_when_symlinks_unavailable(self):
        """Reject a virtual environment root reported as a directory symlink."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            self.mock_runner.get_base_path.return_value = base_path
            venv_path = base_path / ".venv"
            venv_path.mkdir()
            original_is_symlink = Path.is_symlink

            def fake_is_symlink(path_self):
                if path_self == venv_path:
                    return True
                return original_is_symlink(path_self)

            module = PythonVirtualEnvironmentModule()
            with patch.object(Path, "is_symlink", fake_is_symlink):
                with self.assertRaises(DroneException) as context:
                    module.run(self.mock_runner, {"source": ".venv"})

        self.assertEqual(
            str(context.exception),
            f"Virtual environment must not be a symlink: {venv_path}",
        )
        self.mock_runner.set_runner.assert_not_called()

    @patch("builddrone.module.python.python_venv_module.venv.create")
    def test_run_rejects_symlink_interpreter(self, create_venv):
        """Reject an interpreter path that is a symlink before set_runner."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            self.mock_runner.get_base_path.return_value = base_path
            venv_root = base_path / ".venv"
            target = base_path / "evil.py"
            target.write_text("", encoding="utf-8")
            python_executable = venv_root / "bin" / "python"

            def create_environment(_path, **_kwargs):
                python_executable.parent.mkdir(parents=True)
                try:
                    os.symlink(target, python_executable)
                except OSError:
                    self.skipTest("Cannot create symlinks on this platform")

            create_venv.side_effect = create_environment

            module = PythonVirtualEnvironmentModule()
            with self.assertRaises(DroneException) as context:
                module.run(self.mock_runner, {"source": ".venv"})

        self.assertEqual(
            str(context.exception),
            f"Virtual environment interpreter must not be a symlink: {python_executable}",
        )
        self.mock_runner.set_runner.assert_not_called()

    @patch("builddrone.module.python.python_venv_module.venv.create")
    def test_run_rejects_symlink_interpreter_when_symlinks_unavailable(
        self, create_venv
    ):
        """Reject an interpreter path reported as a symlink before set_runner."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            self.mock_runner.get_base_path.return_value = base_path
            python_executable = base_path / ".venv" / "bin" / "python"

            def create_environment(_path, **_kwargs):
                python_executable.parent.mkdir(parents=True)
                python_executable.write_text("", encoding="utf-8")

            create_venv.side_effect = create_environment
            original_is_symlink = Path.is_symlink

            def fake_is_symlink(path_self):
                if path_self == python_executable:
                    return True
                return original_is_symlink(path_self)

            module = PythonVirtualEnvironmentModule()
            with patch.object(Path, "is_symlink", fake_is_symlink):
                with self.assertRaises(DroneException) as context:
                    module.run(self.mock_runner, {"source": ".venv"})

        self.assertEqual(
            str(context.exception),
            f"Virtual environment interpreter must not be a symlink: {python_executable}",
        )
        self.mock_runner.set_runner.assert_not_called()
