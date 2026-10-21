"""Tests for the dotnet test module."""

from unittest.mock import patch

from dotnet_module_test_support import (
    DOTNET,
    WHICH,
    DotnetModuleTestCase,
    plant_file_symlink,
    reported_symlink,
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

    def test_run_rejects_symlinked_results_file(self):
        """Reject TestResults.xml planted inside an otherwise real results directory."""
        results = self.base_path / "results" / "nunit"
        results.mkdir(parents=True)
        planted = results / "TestResults.xml"
        host = plant_file_symlink(self, planted)

        with self.assertRaises(DroneException) as context:
            DotnetTestModule().run(
                self.runner,
                {"environment": "nunit", "results_directory": "results/nunit"},
            )

        self.assertEqual(
            str(context.exception),
            f"Results file must not be a symlink: {planted}",
        )
        self.runner.run_command.assert_not_called()
        self.assertEqual(host.read_text(encoding="utf-8"), "keep\n")

    def test_run_rejects_symlinked_results_file_when_symlinks_unavailable(self):
        """Reject a results file reported as a symlink."""
        results = self.base_path / "results" / "xunit"
        results.mkdir(parents=True)
        planted = results / "TestResults.xml"
        planted.write_text("keep\n", encoding="utf-8")

        with reported_symlink(planted):
            with self.assertRaises(DroneException) as context:
                DotnetTestModule().run(
                    self.runner,
                    {"environment": "xunit", "results_directory": "results/xunit"},
                )

        self.assertEqual(
            str(context.exception),
            f"Results file must not be a symlink: {planted}",
        )
        self.runner.run_command.assert_not_called()

    def test_run_rejects_default_results_symlink(self):
        """Reject TestResults/TestResults.xml when results_directory is omitted."""
        planted = self.base_path / "TestResults" / "TestResults.xml"
        planted.parent.mkdir()
        planted.write_text("keep\n", encoding="utf-8")

        with reported_symlink(planted):
            with self.assertRaises(DroneException) as context:
                DotnetTestModule().run(
                    self.runner,
                    {"environment": "nunit", "project": "App.csproj"},
                )

        self.assertEqual(
            str(context.exception),
            f"Results file must not be a symlink: {planted}",
        )
        self.runner.run_command.assert_not_called()

    def test_run_rejects_default_results_symlink_beside_nested_project(self):
        """Reject the default results file beside the project, not the blueprint root."""
        project_dir = self.base_path / "tests" / "Nested"
        project_dir.mkdir(parents=True)
        project = project_dir / "Nested.csproj"
        project.write_text("<Project />\n", encoding="utf-8")
        planted = project_dir / "TestResults" / "TestResults.xml"
        planted.parent.mkdir()
        planted.write_text("keep\n", encoding="utf-8")

        with reported_symlink(planted):
            with self.assertRaises(DroneException) as context:
                DotnetTestModule().run(
                    self.runner,
                    {
                        "environment": "xunit",
                        "project": "tests/Nested/Nested.csproj",
                    },
                )

        self.assertEqual(
            str(context.exception),
            f"Results file must not be a symlink: {planted}",
        )
        self.runner.run_command.assert_not_called()

    def test_run_rejects_default_results_symlink_in_solution(self):
        """Reject a default results symlink for a project listed in a solution."""
        project_dir = self.base_path / "tests" / "Sample"
        project_dir.mkdir(parents=True)
        project = project_dir / "Sample.csproj"
        project.write_text("<Project />\n", encoding="utf-8")
        solution = self.base_path / "Sample.slnx"
        solution.write_text(
            "<Solution>"
            '<Project Path="tests/Sample/Sample.csproj" />'
            "</Solution>\n",
            encoding="utf-8",
        )
        planted = project_dir / "TestResults" / "TestResults.xml"
        planted.parent.mkdir()
        planted.write_text("keep\n", encoding="utf-8")

        with reported_symlink(planted):
            with self.assertRaises(DroneException) as context:
                DotnetTestModule().run(
                    self.runner,
                    {"environment": "nunit", "project": "Sample.slnx"},
                )

        self.assertEqual(
            str(context.exception),
            f"Results file must not be a symlink: {planted}",
        )
        self.runner.run_command.assert_not_called()

    def test_run_allows_regular_results_file(self):
        """Run when TestResults.xml is a normal file."""
        results = self.base_path / "results"
        results.mkdir()
        (results / "TestResults.xml").write_text("<xml />\n", encoding="utf-8")

        with patch(WHICH, return_value=DOTNET):
            DotnetTestModule().run(
                self.runner,
                {"environment": "nunit", "results_directory": "results"},
            )

        self.assert_command(
            [
                "test",
                "--results-directory",
                str(results),
                "--logger",
                f"nunit;LogFilePath={results / 'TestResults.xml'}",
            ]
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
