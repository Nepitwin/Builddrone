"""Tests for the Python build module."""

# These tests share symlink setup patterns with other python modules.
# pylint: disable=duplicate-code

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from builddrone.drone_exception import DroneException
from builddrone.module.python.python_build_module import PythonBuildModule
from builddrone.runner import Runner


class TestPythonBuildModule(unittest.TestCase):
    """Verify build execution behavior."""

    def setUp(self):
        """Set up a mocked runner."""
        self.mock_runner = MagicMock(spec=Runner)
        self.mock_runner.logger = MagicMock()
        self.mock_runner.get_base_path.return_value = Path("blueprint")

    def test_run_builds_without_arguments(self):
        """Run build with no command arguments."""
        self.mock_runner.run.return_value = 0

        module = PythonBuildModule()
        module.run(self.mock_runner, {})

        self.mock_runner.logger.info.assert_called_with("Building...")
        self.mock_runner.run.assert_called_once_with(
            ["-m", "build"], cwd=str(Path("blueprint"))
        )

    def test_run_ignores_provided_args(self):
        """Run build without passing args to the command."""
        self.mock_runner.run.return_value = 0

        module = PythonBuildModule()
        module.run(self.mock_runner, {"ignored": True})

        self.mock_runner.run.assert_called_once_with(
            ["-m", "build"], cwd=str(Path("blueprint"))
        )

    def test_run_with_nonzero_exit_code_raises(self):
        """Raise when build returns a non-zero exit code."""
        self.mock_runner.run.return_value = 1

        module = PythonBuildModule()

        with self.assertRaises(DroneException) as context:
            module.run(self.mock_runner, {})

        self.assertEqual(str(context.exception), "Build failed with exit code 1")

    def test_run_rejects_symlinked_packaged_file(self):
        """Reject a packaged file that is a symlink before building."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            self.mock_runner.get_base_path.return_value = base_path
            secret = base_path / ".env"
            secret.write_text("PYPI_TOKEN=secret", encoding="utf-8")
            readme = base_path / "README.md"
            try:
                os.symlink(secret, readme)
            except OSError:
                self.skipTest("Cannot create symlinks on this platform")

            module = PythonBuildModule()
            with self.assertRaises(DroneException) as context:
                module.run(self.mock_runner, {})

        self.assertEqual(
            str(context.exception),
            f"Packaged path must not be a symlink: {readme}",
        )
        self.mock_runner.run.assert_not_called()

    def test_run_rejects_symlinked_packaged_file_when_symlinks_unavailable(self):
        """Reject a packaged file reported as a symlink."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            self.mock_runner.get_base_path.return_value = base_path
            readme = base_path / "README.md"
            readme.write_text("docs\n", encoding="utf-8")
            original_is_symlink = Path.is_symlink

            def fake_is_symlink(path_self):
                if path_self == readme:
                    return True
                return original_is_symlink(path_self)

            module = PythonBuildModule()
            with patch.object(Path, "is_symlink", fake_is_symlink):
                with self.assertRaises(DroneException) as context:
                    module.run(self.mock_runner, {})

        self.assertEqual(
            str(context.exception),
            f"Packaged path must not be a symlink: {readme}",
        )
        self.mock_runner.run.assert_not_called()

    def test_run_rejects_nested_symlinked_packaged_file(self):
        """Reject a symlink inside a package directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            self.mock_runner.get_base_path.return_value = base_path
            package = base_path / "src" / "app"
            package.mkdir(parents=True)
            module_path = package / "__init__.py"
            module_path.write_text("value = 1\n", encoding="utf-8")
            original_is_symlink = Path.is_symlink

            def fake_is_symlink(path_self):
                if path_self == module_path:
                    return True
                return original_is_symlink(path_self)

            module = PythonBuildModule()
            with patch.object(Path, "is_symlink", fake_is_symlink):
                with self.assertRaises(DroneException) as context:
                    module.run(self.mock_runner, {})

        self.assertEqual(
            str(context.exception),
            f"Packaged path must not be a symlink: {module_path}",
        )
        self.mock_runner.run.assert_not_called()

    def test_run_rejects_symlinked_packaged_directory(self):
        """Reject a packaged directory that is a symlink."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            self.mock_runner.get_base_path.return_value = base_path
            link_dir = base_path / "pkg"
            link_dir.mkdir()
            original_is_symlink = Path.is_symlink

            def fake_is_symlink(path_self):
                if path_self == link_dir:
                    return True
                return original_is_symlink(path_self)

            module = PythonBuildModule()
            with patch.object(Path, "is_symlink", fake_is_symlink):
                with self.assertRaises(DroneException) as context:
                    module.run(self.mock_runner, {})

        self.assertEqual(
            str(context.exception),
            f"Packaged path must not be a symlink: {link_dir}",
        )
        self.mock_runner.run.assert_not_called()

    def test_run_allows_symlink_inside_virtualenv(self):
        """Build when the only symlink is inside a virtual environment."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            self.mock_runner.get_base_path.return_value = base_path
            self.mock_runner.run.return_value = 0
            (base_path / "README.md").write_text("docs\n", encoding="utf-8")
            venv = base_path / ".venv"
            venv.mkdir()
            link = venv / "lib64"
            link.mkdir()
            original_is_symlink = Path.is_symlink

            def fake_is_symlink(path_self):
                if path_self == link:
                    return True
                return original_is_symlink(path_self)

            module = PythonBuildModule()
            with patch.object(Path, "is_symlink", fake_is_symlink):
                module.run(self.mock_runner, {})

        self.mock_runner.run.assert_called_once_with(
            ["-m", "build"], cwd=str(base_path)
        )
