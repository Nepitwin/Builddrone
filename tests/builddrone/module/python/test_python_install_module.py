"""Tests for the Python install module."""

# These tests share symlink setup patterns with other python modules.
# pylint: disable=duplicate-code

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from builddrone.drone_exception import DroneException
from builddrone.module.python.python_install_module import PythonInstallModule
from builddrone.runner import Runner


class TestPythonInstallModule(unittest.TestCase):
    """Verify install execution behavior."""

    def setUp(self):
        """Set up a mocked runner."""
        self.mock_runner = MagicMock(spec=Runner)
        self.mock_runner.logger = MagicMock()
        self.mock_runner.get_base_path.return_value = Path("blueprint")

    def test_run_installs_source(self):
        """Run pip install against the configured source."""
        self.mock_runner.run.return_value = 0

        module = PythonInstallModule()
        module.run(self.mock_runner, {"source": "build"})

        self.mock_runner.logger.info.assert_called_with("Installing...")
        self.mock_runner.run.assert_called_once_with(
            ["-m", "pip", "install", "--disable-pip-version-check", "build"],
            cwd=str(Path("blueprint")),
        )

    def test_run_without_source_raises(self):
        """Reject missing install source."""
        module = PythonInstallModule()

        with self.assertRaises(DroneException) as context:
            module.run(self.mock_runner, {})

        self.assertEqual(
            str(context.exception),
            "No source or requirements provided for install",
        )
        self.mock_runner.run.assert_not_called()

    def test_run_installs_requirements_file(self):
        """Pass a requirements file to pip as separate arguments."""
        self.mock_runner.run.return_value = 0

        module = PythonInstallModule()
        module.run(self.mock_runner, {"requirements": "requirements.txt"})

        self.mock_runner.run.assert_called_once_with(
            [
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "-r",
                "requirements.txt",
            ],
            cwd=str(Path("blueprint")),
        )

    def test_run_with_nonzero_exit_code_raises(self):
        """Raise when pip install returns a non-zero exit code."""
        self.mock_runner.run.return_value = 1

        module = PythonInstallModule()

        with self.assertRaises(DroneException) as context:
            module.run(self.mock_runner, {"source": "build"})

        self.assertEqual(str(context.exception), "Install failed with exit code 1")

    def test_run_rejects_symlinked_requirements_file(self):
        """Reject a requirements file that is a symlink."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            self.mock_runner.get_base_path.return_value = base_path
            secret = base_path / ".env"
            secret.write_text("PYPI_TOKEN=secret", encoding="utf-8")
            requirements = base_path / "requirements.txt"
            try:
                os.symlink(secret, requirements)
            except OSError:
                self.skipTest("Cannot create symlinks on this platform")

            module = PythonInstallModule()
            with self.assertRaises(DroneException) as context:
                module.run(self.mock_runner, {"requirements": "requirements.txt"})

        self.assertEqual(
            str(context.exception),
            f"Requirements file must not be a symlink: {requirements}",
        )
        self.mock_runner.run.assert_not_called()

    def test_run_rejects_symlinked_requirements_file_when_symlinks_unavailable(self):
        """Reject a requirements file reported as a symlink."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            self.mock_runner.get_base_path.return_value = base_path
            requirements = base_path / "requirements.txt"
            requirements.write_text("build\n", encoding="utf-8")
            original_is_symlink = Path.is_symlink

            def fake_is_symlink(path_self):
                if path_self == requirements:
                    return True
                return original_is_symlink(path_self)

            module = PythonInstallModule()
            with patch.object(Path, "is_symlink", fake_is_symlink):
                with self.assertRaises(DroneException) as context:
                    module.run(self.mock_runner, {"requirements": "requirements.txt"})

        self.assertEqual(
            str(context.exception),
            f"Requirements file must not be a symlink: {requirements}",
        )
        self.mock_runner.run.assert_not_called()

    def test_run_rejects_intermediate_requirements_directory_symlink(self):
        """Reject a requirements path whose prefix is a directory symlink."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            self.mock_runner.get_base_path.return_value = base_path
            host_dir = base_path / "host"
            host_dir.mkdir()
            (host_dir / "requirements.txt").write_text("build\n", encoding="utf-8")
            link_dir = base_path / "deps"
            try:
                os.symlink(host_dir, link_dir, target_is_directory=True)
            except OSError:
                self.skipTest("Cannot create directory symlinks on this platform")

            module = PythonInstallModule()
            with self.assertRaises(DroneException) as context:
                module.run(self.mock_runner, {"requirements": "deps/requirements.txt"})

        self.assertEqual(
            str(context.exception),
            f"Requirements file must not be a symlink: {link_dir}",
        )
        self.mock_runner.run.assert_not_called()

    def test_run_rejects_symlinked_install_source(self):
        """Reject a local install source that is a symlink."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            self.mock_runner.get_base_path.return_value = base_path
            secret = base_path / ".env"
            secret.write_text("PYPI_TOKEN=secret", encoding="utf-8")
            source = base_path / "package"
            try:
                os.symlink(secret, source)
            except OSError:
                self.skipTest("Cannot create symlinks on this platform")

            module = PythonInstallModule()
            with self.assertRaises(DroneException) as context:
                module.run(self.mock_runner, {"source": "package"})

        self.assertEqual(
            str(context.exception),
            f"Install source must not be a symlink: {source}",
        )
        self.mock_runner.run.assert_not_called()

    def test_run_rejects_symlinked_install_source_when_symlinks_unavailable(self):
        """Reject a local install source reported as a symlink."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            self.mock_runner.get_base_path.return_value = base_path
            source = base_path / "package"
            source.mkdir()
            original_is_symlink = Path.is_symlink

            def fake_is_symlink(path_self):
                if path_self == source:
                    return True
                return original_is_symlink(path_self)

            module = PythonInstallModule()
            with patch.object(Path, "is_symlink", fake_is_symlink):
                with self.assertRaises(DroneException) as context:
                    module.run(self.mock_runner, {"source": "package"})

        self.assertEqual(
            str(context.exception),
            f"Install source must not be a symlink: {source}",
        )
        self.mock_runner.run.assert_not_called()
