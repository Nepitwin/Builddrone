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

    def test_run_rejects_symlinked_requirements_include(self):
        """Reject local -r and -c files pip would open from a requirements file."""
        include_lines = (
            "-r secret.txt",
            "--requirement secret.txt",
            "--requirement=secret.txt",
            "-rsecret.txt",
            "-c secret.txt",
            "--constraint=secret.txt",
            "--hash=sha256:abc -r secret.txt",
            "-r \\\nsecret.txt",
        )
        for include_line in include_lines:
            with self.subTest(include_line=include_line):
                self.mock_runner.reset_mock()
                with tempfile.TemporaryDirectory() as temp_dir:
                    base_path = Path(temp_dir)
                    self.mock_runner.get_base_path.return_value = base_path
                    included = base_path / "secret.txt"
                    included.write_text("PYPI_TOKEN=secret\n", encoding="utf-8")
                    requirements = base_path / "requirements.txt"
                    requirements.write_text(f"{include_line}\n", encoding="utf-8")
                    original_is_symlink = Path.is_symlink

                    def fake_is_symlink(
                        path_self,
                        included=included,
                        original_is_symlink=original_is_symlink,
                    ):
                        if path_self == included:
                            return True
                        return original_is_symlink(path_self)

                    module = PythonInstallModule()
                    with patch.object(Path, "is_symlink", fake_is_symlink):
                        with self.assertRaises(DroneException) as context:
                            module.run(
                                self.mock_runner,
                                {"requirements": "requirements.txt"},
                            )

                self.assertEqual(
                    str(context.exception),
                    f"Requirements file must not be a symlink: {included}",
                )
                self.mock_runner.run.assert_not_called()

    def test_run_rejects_symlinked_requirements_include_when_symlinks_unavailable(self):
        """Reject an included requirements file reported as a symlink."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            self.mock_runner.get_base_path.return_value = base_path
            included = base_path / "included.txt"
            included.write_text("PYPI_TOKEN=secret\n", encoding="utf-8")
            requirements = base_path / "requirements.txt"
            requirements.write_text("-r included.txt\n", encoding="utf-8")
            original_is_symlink = Path.is_symlink

            def fake_is_symlink(path_self):
                if path_self == included:
                    return True
                return original_is_symlink(path_self)

            module = PythonInstallModule()
            with patch.object(Path, "is_symlink", fake_is_symlink):
                with self.assertRaises(DroneException) as context:
                    module.run(self.mock_runner, {"requirements": "requirements.txt"})

        self.assertEqual(
            str(context.exception),
            f"Requirements file must not be a symlink: {included}",
        )
        self.mock_runner.run.assert_not_called()

    def test_run_rejects_nested_symlinked_requirements_include(self):
        """Reject a symlink named by a nested include, relative to that file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            self.mock_runner.get_base_path.return_value = base_path
            reqs = base_path / "reqs"
            reqs.mkdir()
            included = reqs / "secret.txt"
            included.write_text("PYPI_TOKEN=secret\n", encoding="utf-8")
            (reqs / "base.txt").write_text("-r secret.txt\n", encoding="utf-8")
            (base_path / "requirements.txt").write_text(
                "-r reqs/base.txt\n", encoding="utf-8"
            )
            original_is_symlink = Path.is_symlink

            def fake_is_symlink(path_self):
                if path_self == included:
                    return True
                return original_is_symlink(path_self)

            module = PythonInstallModule()
            with patch.object(Path, "is_symlink", fake_is_symlink):
                with self.assertRaises(DroneException) as context:
                    module.run(self.mock_runner, {"requirements": "requirements.txt"})

        self.assertEqual(
            str(context.exception),
            f"Requirements file must not be a symlink: {included}",
        )
        self.mock_runner.run.assert_not_called()

    def test_run_rejects_requirements_include_environment_variable(self):
        """Expand pip environment variables before checking include paths."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            self.mock_runner.get_base_path.return_value = base_path
            included = base_path / "secret.txt"
            included.write_text("PYPI_TOKEN=secret\n", encoding="utf-8")
            (base_path / "requirements.txt").write_text(
                "-r ${REQ_INCLUDE}\n", encoding="utf-8"
            )
            original_is_symlink = Path.is_symlink

            def fake_is_symlink(path_self):
                if path_self == included:
                    return True
                return original_is_symlink(path_self)

            module = PythonInstallModule()
            with patch.dict(os.environ, {"REQ_INCLUDE": "secret.txt"}):
                with patch.object(Path, "is_symlink", fake_is_symlink):
                    with self.assertRaises(DroneException) as context:
                        module.run(
                            self.mock_runner, {"requirements": "requirements.txt"}
                        )

        self.assertEqual(
            str(context.exception),
            f"Requirements file must not be a symlink: {included}",
        )
        self.mock_runner.run.assert_not_called()

    def test_run_rejects_file_url_requirements_include(self):
        """Reject a file URL include that points at a symlink."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            self.mock_runner.get_base_path.return_value = base_path
            included = base_path / "secret.txt"
            included.write_text("PYPI_TOKEN=secret\n", encoding="utf-8")
            (base_path / "requirements.txt").write_text(
                "-r file:secret.txt\n", encoding="utf-8"
            )
            original_is_symlink = Path.is_symlink

            def fake_is_symlink(path_self):
                if path_self == included:
                    return True
                return original_is_symlink(path_self)

            module = PythonInstallModule()
            with patch.object(Path, "is_symlink", fake_is_symlink):
                with self.assertRaises(DroneException) as context:
                    module.run(self.mock_runner, {"requirements": "requirements.txt"})

        self.assertEqual(
            str(context.exception),
            f"Requirements file must not be a symlink: {included}",
        )
        self.mock_runner.run.assert_not_called()

    def test_run_installs_requirements_with_regular_include(self):
        """Install when nested requirement and constraint files are regular files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            self.mock_runner.get_base_path.return_value = base_path
            self.mock_runner.run.return_value = 0
            (base_path / "included.txt").write_text("build\n", encoding="utf-8")
            (base_path / "constraints.txt").write_text("build\n", encoding="utf-8")
            (base_path / "requirements.txt").write_text(
                "# -r secret.txt\n-r included.txt\n-c constraints.txt\n",
                encoding="utf-8",
            )

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
            cwd=str(base_path),
        )

    def test_run_ignores_include_on_requirement_line(self):
        """Do not open -r paths that pip ignores on a package requirement line."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            self.mock_runner.get_base_path.return_value = base_path
            self.mock_runner.run.return_value = 0
            included = base_path / "secret.txt"
            included.write_text("PYPI_TOKEN=secret\n", encoding="utf-8")
            (base_path / "requirements.txt").write_text(
                "build -r secret.txt\n", encoding="utf-8"
            )
            original_is_symlink = Path.is_symlink

            def fake_is_symlink(path_self):
                if path_self == included:
                    return True
                return original_is_symlink(path_self)

            module = PythonInstallModule()
            with patch.object(Path, "is_symlink", fake_is_symlink):
                module.run(self.mock_runner, {"requirements": "requirements.txt"})

        self.mock_runner.run.assert_called_once()
