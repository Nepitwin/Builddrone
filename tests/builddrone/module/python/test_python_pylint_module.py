"""Tests for the Python pylint module."""

# These tests share symlink setup patterns with other python modules.
# pylint: disable=duplicate-code,too-many-public-methods

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from builddrone.drone_exception import DroneException
from builddrone.module.python.python_pylint_module import PylintModule
from builddrone.runner import Runner


class TestPylintModule(unittest.TestCase):
    """Verify pylint execution behavior."""

    def setUp(self):
        """Set up a mocked runner."""
        self.mock_runner = MagicMock(spec=Runner)
        self.mock_runner.logger = MagicMock()
        self.mock_runner.get_base_path.return_value = Path("blueprint")

    def test_run_with_paths(self):
        """Run pylint against the configured paths."""
        self.mock_runner.run.return_value = 0

        module = PylintModule()
        module.run(self.mock_runner, {"paths": ["src/builddrone", "tests"]})

        self.mock_runner.logger.info.assert_called_with("Pylint...")
        self.mock_runner.run.assert_called_once_with(
            ["-m", "pylint", "src/builddrone", "tests"],
            cwd=str(Path("blueprint")),
        )

    def test_run_without_targets_raises(self):
        """Reject missing pylint paths and files."""
        module = PylintModule()

        with self.assertRaises(DroneException) as context:
            module.run(self.mock_runner, {})

        self.assertEqual(
            str(context.exception), "No paths or files provided for pylint"
        )
        self.mock_runner.run.assert_not_called()

    def test_run_with_files(self):
        """Run pylint against explicitly configured Python files."""
        self.mock_runner.run.return_value = 0

        module = PylintModule()
        module.run(self.mock_runner, {"files": ["main.py", "tools/check.py"]})

        self.mock_runner.run.assert_called_once_with(
            ["-m", "pylint", "main.py", "tools/check.py"],
            cwd=str(Path("blueprint")),
        )

    def test_run_with_invalid_files_raises(self):
        """Reject files that are not provided as a list of names."""
        module = PylintModule()

        with self.assertRaises(DroneException) as context:
            module.run(self.mock_runner, {"files": "main.py"})

        self.assertEqual(
            str(context.exception), "Files must be a list of non-empty strings"
        )
        self.mock_runner.run.assert_not_called()

    def test_run_with_ignored_names(self):
        """Pass ignored file and directory names to pylint."""
        self.mock_runner.run.return_value = 0

        module = PylintModule()
        module.run(
            self.mock_runner,
            {"paths": ["."], "ignore": [".venv", "build"]},
        )

        self.mock_runner.run.assert_called_once_with(
            ["-m", "pylint", "--ignore", ".venv,build", "."],
            cwd=str(Path("blueprint")),
        )

    def test_run_with_invalid_ignore_raises(self):
        """Reject ignore values that are not lists of names."""
        module = PylintModule()

        with self.assertRaises(DroneException) as context:
            module.run(self.mock_runner, {"paths": ["."], "ignore": ".venv"})

        self.assertEqual(
            str(context.exception), "Ignore must be a list of non-empty strings"
        )
        self.mock_runner.run.assert_not_called()

    def test_run_with_nonzero_exit_code_raises(self):
        """Raise when pylint returns a non-zero exit code."""
        self.mock_runner.run.return_value = 8

        module = PylintModule()

        with self.assertRaises(DroneException) as context:
            module.run(self.mock_runner, {"paths": ["src/builddrone"]})

        self.assertEqual(str(context.exception), "Pylint failed with exit code 8")

    def test_run_rejects_symlinked_file(self):
        """Reject a configured file that is a symlink."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            self.mock_runner.get_base_path.return_value = base_path
            secret = base_path / ".env"
            secret.write_text(
                "GITHUB_TOKEN=ghs_simulated_actions_token_abc123\n",
                encoding="utf-8",
            )
            source = base_path / "main.py"
            try:
                os.symlink(secret, source)
            except OSError:
                self.skipTest("Cannot create symlinks on this platform")

            module = PylintModule()
            with self.assertRaises(DroneException) as context:
                module.run(self.mock_runner, {"files": ["main.py"]})

        self.assertEqual(
            str(context.exception),
            f"Pylint path must not be a symlink: {source}",
        )
        self.mock_runner.run.assert_not_called()

    def test_run_rejects_symlinked_file_when_symlinks_unavailable(self):
        """Reject a configured file reported as a symlink."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            self.mock_runner.get_base_path.return_value = base_path
            source = base_path / "main.py"
            source.write_text("VALUE = 1\n", encoding="utf-8")
            original_is_symlink = Path.is_symlink

            def fake_is_symlink(path_self):
                if path_self == source:
                    return True
                return original_is_symlink(path_self)

            module = PylintModule()
            with patch.object(Path, "is_symlink", fake_is_symlink):
                with self.assertRaises(DroneException) as context:
                    module.run(self.mock_runner, {"files": ["main.py"]})

        self.assertEqual(
            str(context.exception),
            f"Pylint path must not be a symlink: {source}",
        )
        self.mock_runner.run.assert_not_called()

    def test_run_rejects_symlinked_directory(self):
        """Reject a configured directory that is a symlink."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            self.mock_runner.get_base_path.return_value = base_path
            host_dir = base_path / "host"
            host_dir.mkdir()
            (host_dir / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
            link_dir = base_path / "src"
            try:
                os.symlink(host_dir, link_dir, target_is_directory=True)
            except OSError:
                self.skipTest("Cannot create directory symlinks on this platform")

            module = PylintModule()
            with self.assertRaises(DroneException) as context:
                module.run(self.mock_runner, {"paths": ["src"]})

        self.assertEqual(
            str(context.exception),
            f"Pylint path must not be a symlink: {link_dir}",
        )
        self.mock_runner.run.assert_not_called()

    def test_run_rejects_symlinked_directory_when_symlinks_unavailable(self):
        """Reject a configured directory reported as a symlink."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            self.mock_runner.get_base_path.return_value = base_path
            src_dir = base_path / "src"
            src_dir.mkdir()
            (src_dir / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
            original_is_symlink = Path.is_symlink

            def fake_is_symlink(path_self):
                if path_self == src_dir:
                    return True
                return original_is_symlink(path_self)

            module = PylintModule()
            with patch.object(Path, "is_symlink", fake_is_symlink):
                with self.assertRaises(DroneException) as context:
                    module.run(self.mock_runner, {"paths": ["src"]})

        self.assertEqual(
            str(context.exception),
            f"Pylint path must not be a symlink: {src_dir}",
        )
        self.mock_runner.run.assert_not_called()

    def test_run_rejects_walked_symlink_file(self):
        """Reject a symlink file found while walking a linted directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            self.mock_runner.get_base_path.return_value = base_path
            secret = base_path / ".env"
            secret.write_text(
                "GITHUB_TOKEN=ghs_simulated_actions_token_abc123\n",
                encoding="utf-8",
            )
            pkg = base_path / "pkg"
            pkg.mkdir()
            (pkg / "ok.py").write_text("VALUE = 1\n", encoding="utf-8")
            planted = pkg / "leaked.py"
            try:
                os.symlink(secret, planted)
            except OSError:
                self.skipTest("Cannot create symlinks on this platform")

            module = PylintModule()
            with self.assertRaises(DroneException) as context:
                module.run(self.mock_runner, {"paths": ["."]})

        self.assertEqual(
            str(context.exception),
            f"Pylint path must not be a symlink: {planted}",
        )
        self.mock_runner.run.assert_not_called()

    def test_run_rejects_walked_symlink_file_when_symlinks_unavailable(self):
        """Reject a walked file reported as a symlink."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            self.mock_runner.get_base_path.return_value = base_path
            pkg = base_path / "pkg"
            pkg.mkdir()
            planted = pkg / "leaked.py"
            planted.write_text("VALUE = 1\n", encoding="utf-8")
            original_is_symlink = Path.is_symlink

            def fake_is_symlink(path_self):
                if path_self == planted:
                    return True
                return original_is_symlink(path_self)

            module = PylintModule()
            with patch.object(Path, "is_symlink", fake_is_symlink):
                with self.assertRaises(DroneException) as context:
                    module.run(self.mock_runner, {"paths": ["."]})

        self.assertEqual(
            str(context.exception),
            f"Pylint path must not be a symlink: {planted}",
        )
        self.mock_runner.run.assert_not_called()

    def test_run_rejects_walked_directory_symlink(self):
        """Reject a nested directory symlink found while walking a linted path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            self.mock_runner.get_base_path.return_value = base_path
            host_dir = base_path / "host"
            host_dir.mkdir()
            (host_dir / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
            pkg = base_path / "pkg"
            pkg.mkdir()
            link_dir = pkg / "vendor"
            try:
                os.symlink(host_dir, link_dir, target_is_directory=True)
            except OSError:
                self.skipTest("Cannot create directory symlinks on this platform")

            module = PylintModule()
            with self.assertRaises(DroneException) as context:
                module.run(self.mock_runner, {"paths": ["."]})

        self.assertEqual(
            str(context.exception),
            f"Pylint path must not be a symlink: {link_dir}",
        )
        self.mock_runner.run.assert_not_called()

    def test_run_rejects_intermediate_directory_symlink(self):
        """Reject a configured file whose prefix is a directory symlink."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            self.mock_runner.get_base_path.return_value = base_path
            host_dir = base_path / "host"
            host_dir.mkdir()
            (host_dir / "main.py").write_text("VALUE = 1\n", encoding="utf-8")
            link_dir = base_path / "src"
            try:
                os.symlink(host_dir, link_dir, target_is_directory=True)
            except OSError:
                self.skipTest("Cannot create directory symlinks on this platform")

            module = PylintModule()
            with self.assertRaises(DroneException) as context:
                module.run(self.mock_runner, {"files": ["src/main.py"]})

        self.assertEqual(
            str(context.exception),
            f"Pylint path must not be a symlink: {link_dir}",
        )
        self.mock_runner.run.assert_not_called()

    def test_run_rejects_intermediate_directory_symlink_when_symlinks_unavailable(
        self,
    ):
        """Reject a configured file whose prefix is reported as a directory symlink."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            self.mock_runner.get_base_path.return_value = base_path
            src_dir = base_path / "src"
            src_dir.mkdir()
            source = src_dir / "main.py"
            source.write_text("VALUE = 1\n", encoding="utf-8")
            original_is_symlink = Path.is_symlink

            def fake_is_symlink(path_self):
                if path_self == src_dir:
                    return True
                return original_is_symlink(path_self)

            module = PylintModule()
            with patch.object(Path, "is_symlink", fake_is_symlink):
                with self.assertRaises(DroneException) as context:
                    module.run(self.mock_runner, {"files": ["src/main.py"]})

        self.assertEqual(
            str(context.exception),
            f"Pylint path must not be a symlink: {src_dir}",
        )
        self.mock_runner.run.assert_not_called()

    def test_run_skips_symlinks_under_ignored_directory(self):
        """Do not reject symlink files inside ignored directory names."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            self.mock_runner.get_base_path.return_value = base_path
            self.mock_runner.run.return_value = 0
            secret = base_path / ".env"
            secret.write_text("TOKEN=secret\n", encoding="utf-8")
            ignored = base_path / ".venv"
            ignored.mkdir()
            planted = ignored / "leaked.py"
            try:
                os.symlink(secret, planted)
            except OSError:
                self.skipTest("Cannot create symlinks on this platform")
            (base_path / "main.py").write_text("VALUE = 1\n", encoding="utf-8")

            module = PylintModule()
            module.run(
                self.mock_runner,
                {"paths": ["."], "ignore": [".venv"]},
            )

        self.mock_runner.run.assert_called_once_with(
            ["-m", "pylint", "--ignore", ".venv", "."],
            cwd=str(base_path),
        )
