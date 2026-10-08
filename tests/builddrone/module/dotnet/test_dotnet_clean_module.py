"""Tests for the dotnet clean module."""

from pathlib import Path
from unittest.mock import patch

from dotnet_module_test_support import (
    DOTNET,
    WHICH,
    DotnetModuleTestCase,
)

from builddrone.drone_exception import DroneException
from builddrone.module.dotnet.dotnet_clean_module import DotnetCleanModule


class TestDotnetCleanModule(DotnetModuleTestCase):
    """Verify dotnet clean commands and shared argument checks."""

    __test__ = True

    def test_run_cleans_with_optional_arguments(self):
        """Pass project, configuration, framework, runtime, output, and verbosity."""
        with patch(WHICH, return_value=DOTNET):
            DotnetCleanModule().run(
                self.runner,
                {
                    "project": "App.csproj",
                    "configuration": "Release",
                    "framework": "net10.0",
                    "runtime": "win-x64",
                    "output": "artifacts",
                    "verbosity": "minimal",
                },
            )

        self.runner.logger.info.assert_called_with("Cleaning...")
        self.assert_command(
            [
                "clean",
                str(self.project),
                "--configuration",
                "Release",
                "--framework",
                "net10.0",
                "--runtime",
                "win-x64",
                "--output",
                str(self.base_path / "artifacts"),
                "--verbosity",
                "minimal",
            ]
        )

    def test_run_cleans_without_arguments(self):
        """Run dotnet clean in the blueprint directory when no args are set."""
        with patch(WHICH, return_value=DOTNET):
            DotnetCleanModule().run(self.runner, {})

        self.assert_command(["clean"])

    def test_run_rejects_blank_project(self):
        """Reject a blank project path."""
        with self.assertRaises(DroneException) as context:
            DotnetCleanModule().run(self.runner, {"project": "  "})

        self.assertEqual(
            str(context.exception), "Argument 'project' must be a non-empty string"
        )
        self.runner.run_command.assert_not_called()

    def test_run_rejects_missing_project(self):
        """Reject a project path that does not exist."""
        missing = self.base_path / "missing.csproj"
        with self.assertRaises(DroneException) as context:
            DotnetCleanModule().run(self.runner, {"project": "missing.csproj"})

        self.assertEqual(str(context.exception), f"Project not found: {missing}")

    def test_run_rejects_unknown_verbosity(self):
        """Reject verbosity values dotnet does not accept."""
        with self.assertRaises(DroneException) as context:
            DotnetCleanModule().run(self.runner, {"verbosity": "loud"})

        self.assertEqual(
            str(context.exception),
            "Argument 'verbosity' must be one of: "
            "q, m, n, d, diag, quiet, minimal, normal, detailed, diagnostic",
        )

    def test_run_rejects_non_string_configuration(self):
        """Reject configuration values that are not strings."""
        with self.assertRaises(DroneException) as context:
            DotnetCleanModule().run(self.runner, {"configuration": 1})

        self.assertEqual(
            str(context.exception),
            "Argument 'configuration' must be a non-empty string",
        )

    def test_run_rejects_output_file(self):
        """Reject an output path that points at a file."""
        output = self.base_path / "out.txt"
        output.write_text("x", encoding="utf-8")

        with self.assertRaises(DroneException) as context:
            DotnetCleanModule().run(self.runner, {"output": "out.txt"})

        self.assertEqual(
            str(context.exception), f"Output must be a directory: {output}"
        )

    def test_run_rejects_symlinked_project(self):
        """Reject a project path that is a symlink."""
        original_is_symlink = Path.is_symlink

        def fake_is_symlink(path_self):
            if path_self == self.project:
                return True
            return original_is_symlink(path_self)

        with patch.object(Path, "is_symlink", fake_is_symlink):
            with self.assertRaises(DroneException) as context:
                DotnetCleanModule().run(self.runner, {"project": "App.csproj"})

        self.assertEqual(
            str(context.exception),
            f"Project must not be a symlink: {self.project}",
        )
        self.runner.run_command.assert_not_called()

    def test_run_with_nonzero_exit_code_raises(self):
        """Raise when dotnet clean fails."""
        self.runner.run_command.return_value = 2
        with patch(WHICH, return_value=DOTNET):
            with self.assertRaises(DroneException) as context:
                DotnetCleanModule().run(self.runner, {})

        self.assertEqual(str(context.exception), "Clean failed with exit code 2")

    def test_run_requires_dotnet(self):
        """Raise when the dotnet executable is not on PATH."""
        with patch(WHICH, return_value=None):
            with self.assertRaises(DroneException) as context:
                DotnetCleanModule().run(self.runner, {})

        self.assertEqual(str(context.exception), "dotnet is not installed")
