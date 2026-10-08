"""Tests for the dotnet test module."""

from unittest.mock import patch

from dotnet_module_test_support import (
    DOTNET,
    WHICH,
    DotnetModuleTestCase,
)

from builddrone.drone_exception import DroneException
from builddrone.module.dotnet.dotnet_test_module import DotnetTestModule


class TestDotnetTestModule(DotnetModuleTestCase):
    """Verify NUnit and xUnit dotnet test commands."""

    __test__ = True

    def test_run_uses_nunit_logger(self):
        """Select the NUnit logger and pass filter options."""
        with patch(WHICH, return_value=DOTNET):
            DotnetTestModule().run(
                self.runner,
                {
                    "environment": "nunit",
                    "project": "App.csproj",
                    "configuration": "Release",
                    "filter": "Name~Greeter",
                    "no_build": True,
                },
            )

        self.runner.logger.info.assert_called_with("Testing...")
        self.assert_command(
            [
                "test",
                str(self.project),
                "--configuration",
                "Release",
                "--no-build",
                "--filter",
                "Name~Greeter",
                "--logger",
                "nunit;LogFileName=TestResults.xml",
            ]
        )

    def test_run_uses_xunit_logger_and_results_directory(self):
        """Write xUnit results into the configured directory."""
        results = self.base_path / "results"
        with patch(WHICH, return_value=DOTNET):
            DotnetTestModule().run(
                self.runner,
                {"environment": "xunit", "results_directory": "results"},
            )

        self.assert_command(
            [
                "test",
                "--results-directory",
                str(results),
                "--logger",
                f"xunit;LogFilePath={results / 'TestResults.xml'}",
            ]
        )

    def test_run_requires_environment(self):
        """Reject a test step that does not choose nunit or xunit."""
        with self.assertRaises(DroneException) as context:
            DotnetTestModule().run(self.runner, {})

        self.assertEqual(
            str(context.exception),
            "Argument 'environment' must be 'nunit' or 'xunit'",
        )

    def test_run_rejects_unknown_environment(self):
        """Reject test environments other than nunit and xunit."""
        with self.assertRaises(DroneException) as context:
            DotnetTestModule().run(self.runner, {"environment": "mstest"})

        self.assertEqual(
            str(context.exception),
            "Argument 'environment' must be 'nunit' or 'xunit'",
        )

    def test_run_rejects_results_file(self):
        """Reject a results directory that points at a file."""
        results = self.base_path / "results.xml"
        results.write_text("<xml />", encoding="utf-8")

        with self.assertRaises(DroneException) as context:
            DotnetTestModule().run(
                self.runner,
                {"environment": "nunit", "results_directory": "results.xml"},
            )

        self.assertEqual(
            str(context.exception),
            f"Results directory must be a directory: {results}",
        )

    def test_run_with_nonzero_exit_code_raises(self):
        """Raise when dotnet test fails."""
        self.runner.run_command.return_value = 1
        with patch(WHICH, return_value=DOTNET):
            with self.assertRaises(DroneException) as context:
                DotnetTestModule().run(self.runner, {"environment": "nunit"})

        self.assertEqual(str(context.exception), "Test failed with exit code 1")
