"""Tests for the dotnet pack module."""

from unittest.mock import patch

from dotnet_module_test_support import (
    DOTNET,
    WHICH,
    DotnetModuleTestCase,
)

from builddrone.drone_exception import DroneException
from builddrone.module.dotnet.dotnet_pack_module import DotnetPackModule


class TestDotnetPackModule(DotnetModuleTestCase):
    """Verify dotnet pack commands."""

    __test__ = True

    def test_run_packs_with_nuget_options(self):
        """Pass configuration, output, suffix, and package switches."""
        with patch(WHICH, return_value=DOTNET):
            DotnetPackModule().run(
                self.runner,
                {
                    "project": "App.csproj",
                    "configuration": "Release",
                    "output": "artifacts",
                    "verbosity": "q",
                    "version_suffix": "ci",
                    "no_build": True,
                    "no_restore": True,
                    "include_symbols": True,
                    "include_source": True,
                },
            )

        self.runner.logger.info.assert_called_with("Packing...")
        self.assert_command(
            [
                "pack",
                str(self.project),
                "--configuration",
                "Release",
                "--output",
                str(self.base_path / "artifacts"),
                "--verbosity",
                "q",
                "--version-suffix",
                "ci",
                "--no-build",
                "--no-restore",
                "--include-symbols",
                "--include-source",
            ]
        )

    def test_run_omits_optional_pack_switches(self):
        """Pack with only the project when optional switches are left off."""
        with patch(WHICH, return_value=DOTNET):
            DotnetPackModule().run(self.runner, {"project": "App.csproj"})

        self.assert_command(["pack", str(self.project)])

    def test_run_rejects_blank_version_suffix(self):
        """Reject an empty version suffix."""
        with self.assertRaises(DroneException) as context:
            DotnetPackModule().run(self.runner, {"version_suffix": " "})

        self.assertEqual(
            str(context.exception),
            "Argument 'version_suffix' must be a non-empty string",
        )

    def test_run_with_nonzero_exit_code_raises(self):
        """Raise when dotnet pack fails."""
        self.runner.run_command.return_value = 4
        with patch(WHICH, return_value=DOTNET):
            with self.assertRaises(DroneException) as context:
                DotnetPackModule().run(self.runner, {})

        self.assertEqual(str(context.exception), "Pack failed with exit code 4")
