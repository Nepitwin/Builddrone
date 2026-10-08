"""Tests for shared Robot Framework command safety."""

# These tests share symlink setup patterns with other module tests.
# pylint: disable=duplicate-code,too-many-public-methods

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from builddrone.drone_exception import DroneException
from builddrone.module.robotframework.robotframework_rebot_module import (
    RobotframeworkRebotModule,
)
from builddrone.module.robotframework.robotframework_test_module import (
    RobotframeworkTestModule,
)
from builddrone.runner import Runner

_MODULES = (RobotframeworkTestModule, RobotframeworkRebotModule)


class TestRobotframeworkBaseModule(unittest.TestCase):
    """Verify cwd and output path symlink rejection before robot or rebot."""

    def setUp(self):
        """Set up a mocked runner."""
        self.mock_runner = MagicMock(spec=Runner)
        self.mock_runner.logger = MagicMock()
        self.mock_runner.run.return_value = 0

    def _run(self, module, arguments, cwd=None):
        args = {"arguments": arguments}
        if cwd is not None:
            args["cwd"] = cwd
        module.run(self.mock_runner, args)

    def test_run_rejects_symlinked_output_files(self):
        """Reject planted output.xml, log.html, and report.html symlinks."""
        for module_class, file_name in (
            (RobotframeworkTestModule, "output.xml"),
            (RobotframeworkRebotModule, "log.html"),
            (RobotframeworkTestModule, "report.html"),
        ):
            with self.subTest(module=module_class.__name__, file_name=file_name):
                self.mock_runner.reset_mock()
                self.mock_runner.run.return_value = 0
                with tempfile.TemporaryDirectory() as temp_dir:
                    base_path = Path(temp_dir)
                    self.mock_runner.get_base_path.return_value = base_path
                    host_file = base_path / "host.txt"
                    host_file.write_text("keep\n", encoding="utf-8")
                    results = base_path / "results"
                    results.mkdir()
                    planted = results / file_name
                    try:
                        os.symlink(host_file, planted)
                    except OSError:
                        self.skipTest("Cannot create symlinks on this platform")

                    with self.assertRaises(DroneException) as context:
                        self._run(
                            module_class(),
                            [{"--outputdir": "results"}, "tests"],
                        )

                    self.assertEqual(
                        str(context.exception),
                        f"Output path must not be a symlink: {planted}",
                    )
                    self.mock_runner.run.assert_not_called()
                    self.assertEqual(host_file.read_text(encoding="utf-8"), "keep\n")

    def test_run_rejects_symlinked_output_file_when_symlinks_unavailable(self):
        """Reject an output file reported as a symlink."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            self.mock_runner.get_base_path.return_value = base_path
            results = base_path / "results"
            results.mkdir()
            planted = results / "output.xml"
            planted.write_text("keep\n", encoding="utf-8")
            original_is_symlink = Path.is_symlink

            def fake_is_symlink(path_self):
                if path_self == planted:
                    return True
                return original_is_symlink(path_self)

            with patch.object(Path, "is_symlink", fake_is_symlink):
                with self.assertRaises(DroneException) as context:
                    self._run(
                        RobotframeworkTestModule(),
                        [{"--outputdir": "results"}, "tests"],
                    )

        self.assertEqual(
            str(context.exception),
            f"Output path must not be a symlink: {planted}",
        )
        self.mock_runner.run.assert_not_called()

    def test_run_rejects_symlinked_outputdir(self):
        """Reject an outputdir directory symlink that would write outside the workspace."""
        for module_class in _MODULES:
            with self.subTest(module=module_class.__name__):
                self.mock_runner.reset_mock()
                self.mock_runner.run.return_value = 0
                with tempfile.TemporaryDirectory() as temp_dir:
                    base_path = Path(temp_dir)
                    self.mock_runner.get_base_path.return_value = base_path
                    host_dir = base_path / "host"
                    host_dir.mkdir()
                    (host_dir / "keep.txt").write_text("keep\n", encoding="utf-8")
                    results = base_path / "results"
                    try:
                        os.symlink(host_dir, results, target_is_directory=True)
                    except OSError:
                        self.skipTest(
                            "Cannot create directory symlinks on this platform"
                        )

                    with self.assertRaises(DroneException) as context:
                        self._run(
                            module_class(),
                            [{"--outputdir": "results"}, "tests"],
                        )

                self.assertEqual(
                    str(context.exception),
                    f"Output path must not be a symlink: {results}",
                )
                self.mock_runner.run.assert_not_called()

    def test_run_rejects_symlinked_outputdir_when_symlinks_unavailable(self):
        """Reject an outputdir reported as a directory symlink."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            self.mock_runner.get_base_path.return_value = base_path
            results = base_path / "results"
            results.mkdir()
            original_is_symlink = Path.is_symlink

            def fake_is_symlink(path_self):
                if path_self == results:
                    return True
                return original_is_symlink(path_self)

            with patch.object(Path, "is_symlink", fake_is_symlink):
                with self.assertRaises(DroneException) as context:
                    self._run(
                        RobotframeworkRebotModule(),
                        [{"--outputdir": "results"}, "results/output.xml"],
                    )

        self.assertEqual(
            str(context.exception),
            f"Output path must not be a symlink: {results}",
        )
        self.mock_runner.run.assert_not_called()

    def test_run_rejects_symlinked_cwd(self):
        """Reject a working directory that is a symlink."""
        for module_class in _MODULES:
            with self.subTest(module=module_class.__name__):
                self.mock_runner.reset_mock()
                self.mock_runner.run.return_value = 0
                with tempfile.TemporaryDirectory() as temp_dir:
                    base_path = Path(temp_dir)
                    self.mock_runner.get_base_path.return_value = base_path
                    host_dir = base_path / "host"
                    host_dir.mkdir()
                    work = base_path / "work"
                    try:
                        os.symlink(host_dir, work, target_is_directory=True)
                    except OSError:
                        self.skipTest(
                            "Cannot create directory symlinks on this platform"
                        )

                    with self.assertRaises(DroneException) as context:
                        self._run(
                            module_class(),
                            [{"--outputdir": "results"}, "tests"],
                            cwd="work",
                        )

                self.assertEqual(
                    str(context.exception),
                    f"Working directory must not be a symlink: {work}",
                )
                self.mock_runner.run.assert_not_called()

    def test_run_rejects_symlinked_cwd_when_symlinks_unavailable(self):
        """Reject a working directory reported as a symlink."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            self.mock_runner.get_base_path.return_value = base_path
            work = base_path / "work"
            work.mkdir()
            original_is_symlink = Path.is_symlink

            def fake_is_symlink(path_self):
                if path_self == work:
                    return True
                return original_is_symlink(path_self)

            with patch.object(Path, "is_symlink", fake_is_symlink):
                with self.assertRaises(DroneException) as context:
                    self._run(
                        RobotframeworkTestModule(),
                        [{"--outputdir": "results"}, "tests"],
                        cwd="work",
                    )

        self.assertEqual(
            str(context.exception),
            f"Working directory must not be a symlink: {work}",
        )
        self.mock_runner.run.assert_not_called()

    def test_run_rejects_custom_output_name_symlink(self):
        """Reject a custom --output path that is a symlink."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            self.mock_runner.get_base_path.return_value = base_path
            host_file = base_path / "host.txt"
            host_file.write_text("keep\n", encoding="utf-8")
            results = base_path / "results"
            results.mkdir()
            planted = results / "custom.xml"
            try:
                os.symlink(host_file, planted)
            except OSError:
                self.skipTest("Cannot create symlinks on this platform")

            with self.assertRaises(DroneException) as context:
                self._run(
                    RobotframeworkTestModule(),
                    [
                        {"--outputdir": "results"},
                        {"--output": "custom.xml"},
                        "tests",
                    ],
                )

        self.assertEqual(
            str(context.exception),
            f"Output path must not be a symlink: {planted}",
        )
        self.mock_runner.run.assert_not_called()

    def test_run_allows_missing_output_paths(self):
        """Run when outputdir and default result files do not exist yet."""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)
            self.mock_runner.get_base_path.return_value = base_path

            self._run(
                RobotframeworkTestModule(),
                [{"--outputdir": "results"}, "tests"],
            )

        self.mock_runner.run.assert_called_once()
