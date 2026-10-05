"""Tests for the Python run module."""

# These tests share symlink setup patterns with other python modules.
# pylint: disable=duplicate-code

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from builddrone.drone_exception import DroneException
from builddrone.module.python.run_module import PythonRunModule
from builddrone.runner import Runner


class TestPythonRunModule(unittest.TestCase):
    """Verify run execution behavior."""

    def setUp(self):
        """Set up a mocked runner."""
        self.mock_runner = MagicMock(spec=Runner)
        self.mock_runner.logger = MagicMock()
        self.mock_runner.get_base_path.return_value = Path("blueprint")

    def test_run_executes_source(self):
        """Run a Python source file."""
        self.mock_runner.run.return_value = 0

        module = PythonRunModule()
        module.run(self.mock_runner, {"source": "src/app.py"})

        self.mock_runner.logger.info.assert_called_with("Running...")
        self.mock_runner.run.assert_called_once_with(
            ["src/app.py"], cwd=str(Path("blueprint"))
        )

    def test_run_without_source_raises(self):
        """Reject missing source file."""
        module = PythonRunModule()

        with self.assertRaises(DroneException) as context:
            module.run(self.mock_runner, {})

        self.assertEqual(str(context.exception), "No source provided for run")
        self.mock_runner.run.assert_not_called()

    def test_run_with_nonzero_exit_code_raises(self):
        """Raise when the Python file execution fails."""
        self.mock_runner.run.return_value = 2

        module = PythonRunModule()

        with self.assertRaises(DroneException) as context:
            module.run(self.mock_runner, {"source": "src/app.py"})

        self.assertEqual(str(context.exception), "Run failed with exit code 2")

    def test_run_rejects_symlinked_source(self):
        """Reject a source path that is a symlink."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            self.mock_runner.get_base_path.return_value = base_path
            secret = base_path / ".env"
            secret.write_text("PYPI_TOKEN=secret", encoding="utf-8")
            source = base_path / "main.py"
            try:
                os.symlink(secret, source)
            except OSError:
                self.skipTest("Cannot create symlinks on this platform")

            module = PythonRunModule()
            with self.assertRaises(DroneException) as context:
                module.run(self.mock_runner, {"source": "main.py"})

        self.assertEqual(
            str(context.exception),
            f"Source must not be a symlink: {source}",
        )
        self.mock_runner.run.assert_not_called()

    def test_run_rejects_symlinked_source_when_symlinks_unavailable(self):
        """Reject a source path reported as a symlink."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            self.mock_runner.get_base_path.return_value = base_path
            source = base_path / "main.py"
            source.write_text("print('ok')\n", encoding="utf-8")
            original_is_symlink = Path.is_symlink

            def fake_is_symlink(path_self):
                if path_self == source:
                    return True
                return original_is_symlink(path_self)

            module = PythonRunModule()
            with patch.object(Path, "is_symlink", fake_is_symlink):
                with self.assertRaises(DroneException) as context:
                    module.run(self.mock_runner, {"source": "main.py"})

        self.assertEqual(
            str(context.exception),
            f"Source must not be a symlink: {source}",
        )
        self.mock_runner.run.assert_not_called()

    def test_run_rejects_intermediate_source_directory_symlink(self):
        """Reject a source path whose prefix is a directory symlink."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            self.mock_runner.get_base_path.return_value = base_path
            host_dir = base_path / "host"
            host_dir.mkdir()
            (host_dir / "main.py").write_text("print('ok')\n", encoding="utf-8")
            link_dir = base_path / "src"
            try:
                os.symlink(host_dir, link_dir, target_is_directory=True)
            except OSError:
                self.skipTest("Cannot create directory symlinks on this platform")

            module = PythonRunModule()
            with self.assertRaises(DroneException) as context:
                module.run(self.mock_runner, {"source": "src/main.py"})

        self.assertEqual(
            str(context.exception),
            f"Source must not be a symlink: {link_dir}",
        )
        self.mock_runner.run.assert_not_called()

    def test_run_rejects_intermediate_source_directory_symlink_when_symlinks_unavailable(
        self,
    ):
        """Reject a source path whose prefix is reported as a directory symlink."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            self.mock_runner.get_base_path.return_value = base_path
            src_dir = base_path / "src"
            src_dir.mkdir()
            source = src_dir / "main.py"
            source.write_text("print('ok')\n", encoding="utf-8")
            original_is_symlink = Path.is_symlink

            def fake_is_symlink(path_self):
                if path_self == src_dir:
                    return True
                return original_is_symlink(path_self)

            module = PythonRunModule()
            with patch.object(Path, "is_symlink", fake_is_symlink):
                with self.assertRaises(DroneException) as context:
                    module.run(self.mock_runner, {"source": "src/main.py"})

        self.assertEqual(
            str(context.exception),
            f"Source must not be a symlink: {src_dir}",
        )
        self.mock_runner.run.assert_not_called()
