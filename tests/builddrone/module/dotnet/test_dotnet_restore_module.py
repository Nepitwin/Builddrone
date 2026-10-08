"""Tests for the dotnet restore module."""

from unittest.mock import patch

from dotnet_module_test_support import (
    DOTNET,
    WHICH,
    DotnetModuleTestCase,
)

from builddrone.drone_exception import DroneException
from builddrone.module.dotnet.dotnet_restore_module import DotnetRestoreModule


class TestDotnetRestoreModule(DotnetModuleTestCase):
    """Verify dotnet restore commands."""

    __test__ = True

    def test_run_restores_sources_and_force(self):
        """Pass project, sources, runtime, verbosity, and --force."""
        with patch(WHICH, return_value=DOTNET):
            DotnetRestoreModule().run(
                self.runner,
                {
                    "project": "App.csproj",
                    "sources": [
                        "https://api.nuget.org/v3/index.json",
                        "https://example.test/v3/index.json",
                    ],
                    "runtime": "win-x64",
                    "verbosity": "n",
                    "force": True,
                },
            )

        self.runner.logger.info.assert_called_with("Restoring...")
        self.assert_command(
            [
                "restore",
                str(self.project),
                "--source",
                "https://api.nuget.org/v3/index.json",
                "--source",
                "https://example.test/v3/index.json",
                "--runtime",
                "win-x64",
                "--verbosity",
                "n",
                "--force",
            ]
        )

    def test_run_omits_force_by_default(self):
        """Do not pass --force unless it is enabled."""
        with patch(WHICH, return_value=DOTNET):
            DotnetRestoreModule().run(self.runner, {"project": "App.csproj"})

        self.assert_command(["restore", str(self.project)])

    def test_run_rejects_sources_that_are_not_a_list(self):
        """Reject a single string used where a source list is required."""
        with self.assertRaises(DroneException) as context:
            DotnetRestoreModule().run(self.runner, {"sources": "https://example.test"})

        self.assertEqual(str(context.exception), "Argument 'sources' must be a list")

    def test_run_rejects_blank_source(self):
        """Reject an empty NuGet source entry."""
        with self.assertRaises(DroneException) as context:
            DotnetRestoreModule().run(self.runner, {"sources": ["  "]})

        self.assertEqual(
            str(context.exception),
            "Argument 'sources' must contain non-empty strings",
        )

    def test_run_rejects_non_boolean_force(self):
        """Reject force values that are not booleans."""
        with self.assertRaises(DroneException) as context:
            DotnetRestoreModule().run(self.runner, {"force": "yes"})

        self.assertEqual(str(context.exception), "Argument 'force' must be a boolean")

    def test_run_with_nonzero_exit_code_raises(self):
        """Raise when dotnet restore fails."""
        self.runner.run_command.return_value = 1
        with patch(WHICH, return_value=DOTNET):
            with self.assertRaises(DroneException) as context:
                DotnetRestoreModule().run(self.runner, {})

        self.assertEqual(str(context.exception), "Restore failed with exit code 1")
