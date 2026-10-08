"""Tests for the dotnet nuget push module."""

import os
from unittest.mock import patch

from dotnet_module_test_support import (
    DOTNET,
    WHICH,
    DotnetModuleTestCase,
)

from builddrone.drone_exception import DroneException
from builddrone.module.dotnet.dotnet_nuget_push_module import DotnetNugetPushModule


class TestDotnetNugetPushModule(DotnetModuleTestCase):
    """Verify NuGet package deployment."""

    __test__ = True

    def setUp(self):
        """Create sample packages beside the temporary project."""
        super().setUp()
        self.artifacts = self.base_path / "artifacts"
        self.artifacts.mkdir()
        self.package = self.artifacts / "Example.1.0.0.nupkg"
        self.package.write_bytes(b"package")
        self.symbols = self.artifacts / "Example.1.0.0.snupkg"
        self.symbols.write_bytes(b"symbols")
        (self.artifacts / "notes.txt").write_text("ignore", encoding="utf-8")
        self.module = DotnetNugetPushModule()

    def test_run_pushes_packages_and_skips_duplicates_by_default(self):
        """Push nupkg and snupkg files and pass --skip-duplicate."""
        with patch(WHICH, return_value=DOTNET):
            with patch.dict(os.environ, {"NUGET_API_KEY": "test-key"}):
                self.module.run(
                    self.runner,
                    {
                        "packages": ["artifacts/*"],
                        "source": "https://api.nuget.org/v3/index.json",
                        "api_key_env": "NUGET_API_KEY",
                    },
                )

        self.runner.logger.info.assert_any_call("Pushing NuGet packages...")
        self.assertEqual(self.runner.run_command.call_count, 2)
        self.runner.run_command.assert_any_call(
            [
                DOTNET,
                "nuget",
                "push",
                str(self.package),
                "--source",
                "https://api.nuget.org/v3/index.json",
                "--api-key",
                "test-key",
                "--skip-duplicate",
            ],
            cwd=str(self.base_path),
        )
        self.runner.run_command.assert_any_call(
            [
                DOTNET,
                "nuget",
                "push",
                str(self.symbols),
                "--source",
                "https://api.nuget.org/v3/index.json",
                "--api-key",
                "test-key",
                "--skip-duplicate",
            ],
            cwd=str(self.base_path),
        )

    def test_run_can_disable_skip_duplicate_and_push_symbols(self):
        """Pass symbol server options and omit --skip-duplicate when disabled."""
        with patch(WHICH, return_value=DOTNET):
            with patch.dict(
                os.environ,
                {"NUGET_API_KEY": "test-key", "NUGET_SYMBOL_KEY": "symbol-key"},
            ):
                self.module.run(
                    self.runner,
                    {
                        "packages": ["artifacts/*.nupkg"],
                        "source": "https://example.test/v3/index.json",
                        "api_key_env": "NUGET_API_KEY",
                        "skip_duplicate": False,
                        "symbol_source": "https://example.test/symbols",
                        "symbol_api_key_env": "NUGET_SYMBOL_KEY",
                    },
                )

        self.runner.run_command.assert_called_once_with(
            [
                DOTNET,
                "nuget",
                "push",
                str(self.package),
                "--source",
                "https://example.test/v3/index.json",
                "--api-key",
                "test-key",
                "--symbol-source",
                "https://example.test/symbols",
                "--symbol-api-key",
                "symbol-key",
            ],
            cwd=str(self.base_path),
        )

    def test_run_rejects_inline_api_key(self):
        """Refuse an API key stored in the blueprint."""
        with self.assertRaises(DroneException) as context:
            self.module.run(
                self.runner,
                {
                    "packages": ["artifacts/*.nupkg"],
                    "source": "https://example.test/v3/index.json",
                    "api_key": "test-key",
                    "api_key_env": "NUGET_API_KEY",
                },
            )

        self.assertEqual(
            str(context.exception),
            "Argument 'api_key' is not supported; "
            "use an environment variable name instead",
        )
        self.runner.run_command.assert_not_called()

    def test_run_requires_api_key_environment_variable(self):
        """Raise when the named environment variable is missing."""
        environ = os.environ.copy()
        environ.pop("NUGET_API_KEY", None)
        with patch.dict(os.environ, environ, clear=True):
            with self.assertRaises(DroneException) as context:
                self.module.run(
                    self.runner,
                    {
                        "packages": ["artifacts/*.nupkg"],
                        "source": "https://example.test/v3/index.json",
                        "api_key_env": "NUGET_API_KEY",
                    },
                )

        self.assertEqual(
            str(context.exception), "Environment variable 'NUGET_API_KEY' is not set"
        )

    def test_run_rejects_unmatched_pattern(self):
        """Raise when a glob matches no packages."""
        with patch.dict(os.environ, {"NUGET_API_KEY": "test-key"}):
            with self.assertRaises(DroneException) as context:
                self.module.run(
                    self.runner,
                    {
                        "packages": ["missing/*.nupkg"],
                        "source": "https://example.test/v3/index.json",
                        "api_key_env": "NUGET_API_KEY",
                    },
                )

        self.assertEqual(
            str(context.exception), "No files matched pattern: missing/*.nupkg"
        )

    def test_run_rejects_empty_package_list(self):
        """Reject a blueprint that does not select any packages."""
        with self.assertRaises(DroneException) as context:
            self.module.run(self.runner, {"packages": []})

        self.assertEqual(
            str(context.exception), "Argument 'packages' must be a non-empty list"
        )

    def test_run_requires_dotnet(self):
        """Raise when packages are ready but dotnet is missing."""
        with patch(WHICH, return_value=None):
            with patch.dict(os.environ, {"NUGET_API_KEY": "test-key"}):
                with self.assertRaises(DroneException) as context:
                    self.module.run(
                        self.runner,
                        {
                            "packages": ["artifacts/*.nupkg"],
                            "source": "https://example.test/v3/index.json",
                            "api_key_env": "NUGET_API_KEY",
                        },
                    )

        self.assertEqual(str(context.exception), "dotnet is not installed")

    def test_run_with_nonzero_exit_code_raises(self):
        """Raise when nuget push fails for a package."""
        self.runner.run_command.return_value = 1
        with patch(WHICH, return_value=DOTNET):
            with patch.dict(os.environ, {"NUGET_API_KEY": "test-key"}):
                with self.assertRaises(DroneException) as context:
                    self.module.run(
                        self.runner,
                        {
                            "packages": ["artifacts/*.nupkg"],
                            "source": "https://example.test/v3/index.json",
                            "api_key_env": "NUGET_API_KEY",
                        },
                    )

        self.assertEqual(
            str(context.exception),
            "NuGet push failed for 'Example.1.0.0.nupkg' with exit code 1",
        )
