"""Tests for the dotnet build module."""

from unittest.mock import patch

from dotnet_module_test_support import (
    DOTNET,
    WHICH,
    DotnetModuleTestCase,
)

from builddrone.drone_exception import DroneException
from builddrone.module.dotnet.dotnet_build_module import DotnetBuildModule


class TestDotnetBuildModule(DotnetModuleTestCase):
    """Verify dotnet build commands."""

    __test__ = True

    def test_run_builds_without_restore(self):
        """Pass the project, configuration, and --no-restore."""
        with patch(WHICH, return_value=DOTNET):
            DotnetBuildModule().run(
                self.runner,
                {
                    "project": "App.csproj",
                    "configuration": "Release",
                    "no_restore": True,
                },
            )

        self.runner.logger.info.assert_called_with("Building...")
        self.assert_command(
            [
                "build",
                str(self.project),
                "--configuration",
                "Release",
                "--no-restore",
            ]
        )

    def test_run_omits_no_restore_when_disabled(self):
        """Leave --no-restore off when the flag is false."""
        with patch(WHICH, return_value=DOTNET):
            DotnetBuildModule().run(
                self.runner,
                {"project": "App.csproj", "no_restore": False},
            )

        self.assert_command(["build", str(self.project)])

    def test_run_rejects_non_boolean_no_restore(self):
        """Reject no_restore values that are not booleans."""
        with self.assertRaises(DroneException) as context:
            DotnetBuildModule().run(self.runner, {"no_restore": "true"})

        self.assertEqual(
            str(context.exception), "Argument 'no_restore' must be a boolean"
        )

    def test_run_with_nonzero_exit_code_raises(self):
        """Raise when dotnet build fails."""
        self.runner.run_command.return_value = 1
        with patch(WHICH, return_value=DOTNET):
            with self.assertRaises(DroneException) as context:
                DotnetBuildModule().run(self.runner, {})

        self.assertEqual(str(context.exception), "Build failed with exit code 1")
