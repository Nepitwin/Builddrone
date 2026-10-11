"""Tests for the dotnet pack module."""

from unittest.mock import patch

from dotnet_module_test_support import (
    DOTNET,
    WHICH,
    DotnetModuleTestCase,
    plant_file_symlink,
    reported_symlink,
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

    def test_run_rejects_symlinked_package(self):
        """Reject a package file planted in an otherwise real output directory."""
        self._write_package_project("Builddrone.DotnetExample", "1.0.0")
        artifacts = self.base_path / "artifacts"
        artifacts.mkdir()
        planted = artifacts / "Builddrone.DotnetExample.1.0.0.nupkg"
        host = plant_file_symlink(self, planted)

        with self.assertRaises(DroneException) as context:
            self._pack_example()

        self.assertEqual(
            str(context.exception),
            f"Package must not be a symlink: {planted}",
        )
        self.runner.run_command.assert_not_called()
        self.assertEqual(host.read_text(encoding="utf-8"), "keep\n")

    def test_run_rejects_symlinked_package_when_symlinks_unavailable(self):
        """Reject a package file reported as a symlink."""
        self._write_package_project("Builddrone.DotnetExample", "1.0.0")
        planted = self.base_path / "artifacts" / "Builddrone.DotnetExample.1.0.0.nupkg"
        planted.parent.mkdir()
        planted.write_bytes(b"keep")

        with reported_symlink(planted):
            with self.assertRaises(DroneException) as context:
                self._pack_example()

        self.assertEqual(
            str(context.exception),
            f"Package must not be a symlink: {planted}",
        )
        self.runner.run_command.assert_not_called()

    def test_run_rejects_symlinked_package_from_project_file_name(self):
        """Use the project file name when PackageId is omitted."""
        project_dir = self.base_path / "src" / "Builddrone.DotnetExample"
        project_dir.mkdir(parents=True)
        project = project_dir / "Builddrone.DotnetExample.csproj"
        project.write_text(
            "<Project><PropertyGroup><Version>1.0.0</Version></PropertyGroup></Project>",
            encoding="utf-8",
        )
        planted = self.base_path / "artifacts" / "Builddrone.DotnetExample.1.0.0.nupkg"
        planted.parent.mkdir()
        planted.write_bytes(b"keep")

        with reported_symlink(planted):
            with self.assertRaises(DroneException) as context:
                DotnetPackModule().run(
                    self.runner,
                    {
                        "project": (
                            "src/Builddrone.DotnetExample/"
                            "Builddrone.DotnetExample.csproj"
                        ),
                        "output": "artifacts",
                    },
                )

        self.assertEqual(
            str(context.exception),
            f"Package must not be a symlink: {planted}",
        )
        self.runner.run_command.assert_not_called()

    def test_run_rejects_symlinked_symbol_packages(self):
        """Reject both symbol package names when symbols are included."""
        self._write_package_project("Example", "1.0.0")
        artifacts = self.base_path / "artifacts"
        artifacts.mkdir()
        for name in ("Example.1.0.0.snupkg", "Example.1.0.0.symbols.nupkg"):
            planted = artifacts / name
            planted.write_bytes(b"keep")
            with self.subTest(name=name):
                self.runner.run_command.reset_mock()
                self.runner.run_command.return_value = 0
                with reported_symlink(planted):
                    with self.assertRaises(DroneException) as context:
                        DotnetPackModule().run(
                            self.runner,
                            {
                                "project": "App.csproj",
                                "output": "artifacts",
                                "include_symbols": True,
                            },
                        )
                self.assertEqual(
                    str(context.exception),
                    f"Package must not be a symlink: {planted}",
                )
                self.runner.run_command.assert_not_called()

    def test_run_ignores_symbol_symlink_without_include_symbols(self):
        """Leave a symbol-package symlink alone when symbols are not created."""
        self._write_package_project("Example", "1.0.0")
        artifacts = self.base_path / "artifacts"
        artifacts.mkdir()
        planted = artifacts / "Example.1.0.0.snupkg"
        planted.write_bytes(b"keep")

        with reported_symlink(planted):
            with patch(WHICH, return_value=DOTNET):
                DotnetPackModule().run(
                    self.runner,
                    {"project": "App.csproj", "output": "artifacts"},
                )

        self.runner.run_command.assert_called_once()

    def test_run_rejects_default_package_path(self):
        """Reject the package under bin/Configuration when output is omitted."""
        self._write_package_project("Example", "1.0.0")
        planted = self.base_path / "bin" / "Release" / "Example.1.0.0.nupkg"
        planted.parent.mkdir(parents=True)
        planted.write_bytes(b"keep")

        with reported_symlink(planted):
            with self.assertRaises(DroneException) as context:
                DotnetPackModule().run(
                    self.runner,
                    {"project": "App.csproj", "configuration": "Release"},
                )

        self.assertEqual(
            str(context.exception),
            f"Package must not be a symlink: {planted}",
        )
        self.runner.run_command.assert_not_called()

    def test_run_normalizes_package_version(self):
        """Reject the normalized file name, such as 1.2 becoming 1.2.0."""
        self._write_package_project("Example", "1.2")
        artifacts = self.base_path / "artifacts"
        artifacts.mkdir()
        unnormalized = artifacts / "Example.1.2.nupkg"
        normalized = artifacts / "Example.1.2.0.nupkg"
        unnormalized.write_bytes(b"keep")
        normalized.write_bytes(b"keep")

        with reported_symlink(unnormalized):
            with patch(WHICH, return_value=DOTNET):
                DotnetPackModule().run(
                    self.runner,
                    {"project": "App.csproj", "output": "artifacts"},
                )
        self.runner.run_command.assert_called_once()

        self.runner.run_command.reset_mock()
        self.runner.run_command.return_value = 0
        with reported_symlink(normalized):
            with self.assertRaises(DroneException) as context:
                DotnetPackModule().run(
                    self.runner,
                    {"project": "App.csproj", "output": "artifacts"},
                )
        self.assertEqual(
            str(context.exception),
            f"Package must not be a symlink: {normalized}",
        )

    def test_run_appends_version_suffix_when_version_is_omitted(self):
        """Build the package name from VersionPrefix and version_suffix."""
        self.project.write_text(
            "<Project><PropertyGroup>"
            "<VersionPrefix>1.2.0</VersionPrefix>"
            "<PackageId>Example</PackageId>"
            "</PropertyGroup></Project>",
            encoding="utf-8",
        )
        planted = self.base_path / "artifacts" / "Example.1.2.0-beta.nupkg"
        planted.parent.mkdir()
        planted.write_bytes(b"keep")

        with reported_symlink(planted):
            with self.assertRaises(DroneException) as context:
                DotnetPackModule().run(
                    self.runner,
                    {
                        "project": "App.csproj",
                        "output": "artifacts",
                        "version_suffix": "beta",
                    },
                )

        self.assertEqual(
            str(context.exception),
            f"Package must not be a symlink: {planted}",
        )

    def test_run_keeps_explicit_version_when_suffix_is_set(self):
        """Do not append version_suffix when Version is already set."""
        self._write_package_project("Example", "2.3.4")
        artifacts = self.base_path / "artifacts"
        artifacts.mkdir()
        suffixed = artifacts / "Example.2.3.4-ci.nupkg"
        explicit = artifacts / "Example.2.3.4.nupkg"
        suffixed.write_bytes(b"keep")
        explicit.write_bytes(b"keep")

        with reported_symlink(suffixed):
            with patch(WHICH, return_value=DOTNET):
                DotnetPackModule().run(
                    self.runner,
                    {
                        "project": "App.csproj",
                        "output": "artifacts",
                        "version_suffix": "ci",
                    },
                )
        self.runner.run_command.assert_called_once()

        self.runner.run_command.reset_mock()
        self.runner.run_command.return_value = 0
        with reported_symlink(explicit):
            with self.assertRaises(DroneException) as context:
                DotnetPackModule().run(
                    self.runner,
                    {
                        "project": "App.csproj",
                        "output": "artifacts",
                        "version_suffix": "ci",
                    },
                )
        self.assertEqual(
            str(context.exception),
            f"Package must not be a symlink: {explicit}",
        )

    def test_run_uses_directory_build_props_and_project_override(self):
        """Let the project Version override Directory.Build.props."""
        (self.base_path / "Directory.Build.props").write_text(
            "<Project><PropertyGroup>"
            "<Version>9.9.9</Version>"
            "<PackageId>FromProps</PackageId>"
            "</PropertyGroup></Project>",
            encoding="utf-8",
        )
        self._write_package_project(None, "3.0.0")
        planted = self.base_path / "artifacts" / "FromProps.3.0.0.nupkg"
        planted.parent.mkdir()
        planted.write_bytes(b"keep")

        with reported_symlink(planted):
            with self.assertRaises(DroneException) as context:
                DotnetPackModule().run(
                    self.runner,
                    {"project": "App.csproj", "output": "artifacts"},
                )

        self.assertEqual(
            str(context.exception),
            f"Package must not be a symlink: {planted}",
        )

    def test_run_lets_directory_build_targets_override_version(self):
        """Use Version from Directory.Build.targets when it overrides the project."""
        self._write_package_project("Example", "3.0.0")
        (self.base_path / "Directory.Build.targets").write_text(
            "<Project><PropertyGroup><Version>8.8.8</Version></PropertyGroup></Project>",
            encoding="utf-8",
        )
        planted = self.base_path / "artifacts" / "Example.8.8.8.nupkg"
        planted.parent.mkdir()
        planted.write_bytes(b"keep")

        with reported_symlink(planted):
            with self.assertRaises(DroneException) as context:
                DotnetPackModule().run(
                    self.runner,
                    {"project": "App.csproj", "output": "artifacts"},
                )

        self.assertEqual(
            str(context.exception),
            f"Package must not be a symlink: {planted}",
        )

    def test_run_skips_non_packable_project(self):
        """Do not treat a package path as output when IsPackable is false."""
        self.project.write_text(
            "<Project><PropertyGroup>"
            "<Version>1.0.0</Version>"
            "<PackageId>Example</PackageId>"
            "<IsPackable>false</IsPackable>"
            "</PropertyGroup></Project>",
            encoding="utf-8",
        )
        planted = self.base_path / "artifacts" / "Example.1.0.0.nupkg"
        planted.parent.mkdir()
        planted.write_bytes(b"keep")

        with reported_symlink(planted):
            with patch(WHICH, return_value=DOTNET):
                DotnetPackModule().run(
                    self.runner,
                    {"project": "App.csproj", "output": "artifacts"},
                )

        self.runner.run_command.assert_called_once()

    def test_run_allows_regular_package_file(self):
        """Pack when the output nupkg is a normal file."""
        self._write_package_project("Example", "1.0.0")
        package = self.base_path / "artifacts" / "Example.1.0.0.nupkg"
        package.parent.mkdir()
        package.write_bytes(b"package")

        with patch(WHICH, return_value=DOTNET):
            DotnetPackModule().run(
                self.runner,
                {"project": "App.csproj", "output": "artifacts"},
            )

        self.runner.run_command.assert_called_once()

    def _write_package_project(self, package_id, version):
        """Replace the fixture project with an unconditional package identity."""
        identity = f"<Version>{version}</Version>"
        if package_id is not None:
            identity = f"<PackageId>{package_id}</PackageId>{identity}"
        self.project.write_text(
            f"<Project><PropertyGroup>{identity}</PropertyGroup></Project>",
            encoding="utf-8",
        )

    def _pack_example(self):
        """Pack the fixture project into artifacts."""
        DotnetPackModule().run(
            self.runner,
            {"project": "App.csproj", "output": "artifacts"},
        )

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
