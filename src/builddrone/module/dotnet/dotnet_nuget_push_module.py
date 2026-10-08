"""dotnet nuget push module."""

from __future__ import annotations

import glob
import os
from pathlib import Path

from builddrone.drone_exception import DroneException
from builddrone.module.dotnet.dotnet_base_module import DotnetBaseModule
from builddrone.path_safety import reject_symlink_component
from builddrone.runner import Runner

_PACKAGE_SUFFIXES = {".nupkg", ".snupkg"}
_INLINE_SECRET_ARGUMENTS = ("api_key", "symbol_api_key")


class DotnetNugetPushModule(DotnetBaseModule):  # pylint: disable=too-few-public-methods
    """Deploy NuGet packages with ``dotnet nuget push``.

    API keys are read from environment variables named by the blueprint.
    Put the key in the CI environment, not in ``blueprint.json``.

    Blueprint configuration arguments:
        "packages": "Non-empty list of glob patterns selecting .nupkg files"
        "source": "NuGet source URL or name"
        "api_key_env": "Environment variable that holds the API key"
        "skip_duplicate": "Skip packages that already exist (default: true)"
        "symbol_source": "Optional symbol server URL or name"
        "symbol_api_key_env": "Optional environment variable for the symbol key"
    """

    log_message = "Pushing NuGet packages..."
    failure_label = "NuGet push"

    def run(self, runner: Runner, args: dict) -> None:
        """Push each package matched by the configured glob patterns."""
        self._reject_inline_secrets(args)
        patterns = self._require_packages(args)
        source = self._require_string(args, "source")
        api_key = self._environment_value(args, "api_key_env")
        skip_duplicate = self._optional_bool(args, "skip_duplicate", default=True)
        symbol_source = self._optional_string(args, "symbol_source")
        symbol_api_key = self._optional_environment_value(args, "symbol_api_key_env")

        base_path = Path(runner.get_base_path())
        packages = self._collect_packages(patterns, base_path)
        runner.logger.info(self.log_message)
        dotnet = self._dotnet_executable()

        for package in packages:
            self._push_package(
                runner,
                base_path,
                dotnet,
                package,
                source,
                api_key,
                skip_duplicate,
                symbol_source,
                symbol_api_key,
            )

    def _collect_packages(self, patterns: list[str], base_path: Path) -> list[Path]:
        """Return every package selected by ``patterns``."""
        packages: list[Path] = []
        for pattern in patterns:
            matched_packages = self._matching_packages(pattern, base_path)
            if not matched_packages:
                raise DroneException(f"No files matched pattern: {pattern}")
            packages.extend(matched_packages)
        return packages

    def _push_package(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        runner: Runner,
        base_path: Path,
        dotnet: str,
        package: Path,
        source: str,
        api_key: str,
        skip_duplicate: bool,
        symbol_source: str | None,
        symbol_api_key: str | None,
    ) -> None:
        """Push one package and raise when dotnet fails."""
        command = [
            dotnet,
            "nuget",
            "push",
            str(package),
            "--source",
            source,
            "--api-key",
            api_key,
        ]
        if skip_duplicate:
            command.append("--skip-duplicate")
        if symbol_source is not None:
            command.extend(["--symbol-source", symbol_source])
        if symbol_api_key is not None:
            command.extend(["--symbol-api-key", symbol_api_key])

        runner.logger.info("Pushing %s", package.name)
        exit_code = runner.run_command(command, cwd=str(base_path))
        if exit_code != 0:
            raise DroneException(
                f"NuGet push failed for '{package.name}' with exit code {exit_code}"
            )

    @staticmethod
    def _reject_inline_secrets(args: dict) -> None:
        """Refuse API keys stored directly in the blueprint."""
        for name in _INLINE_SECRET_ARGUMENTS:
            if name in args:
                raise DroneException(
                    f"Argument '{name}' is not supported; "
                    "use an environment variable name instead"
                )

    @staticmethod
    def _require_packages(args: dict) -> list[str]:
        """Return the configured package glob patterns."""
        packages = args.get("packages")
        if not isinstance(packages, list) or not packages:
            raise DroneException("Argument 'packages' must be a non-empty list")

        for pattern in packages:
            if not isinstance(pattern, str) or not pattern.strip():
                raise DroneException(
                    "Argument 'packages' must contain non-empty strings"
                )
        return packages

    def _require_string(self, args: dict, name: str) -> str:
        """Return a required non-empty string argument."""
        value = self._optional_string(args, name)
        if value is None:
            raise DroneException(f"Argument '{name}' must be a non-empty string")
        return value

    def _environment_value(self, args: dict, name: str) -> str:
        """Read a required secret from the environment variable named in ``args``."""
        variable = self._require_string(args, name)
        secret = os.environ.get(variable)
        if not secret:
            raise DroneException(f"Environment variable '{variable}' is not set")
        return secret

    def _optional_environment_value(self, args: dict, name: str) -> str | None:
        """Read an optional secret when its environment variable name is set."""
        variable = self._optional_string(args, name)
        if variable is None:
            return None
        secret = os.environ.get(variable)
        if not secret:
            raise DroneException(f"Environment variable '{variable}' is not set")
        return secret

    def _matching_packages(self, pattern: str, base_path: Path) -> list[Path]:
        """Return package files that match ``pattern`` under ``base_path``."""
        search_pattern = pattern
        if not os.path.isabs(pattern):
            search_pattern = str(base_path / pattern)

        matched_packages: list[Path] = []
        for match in glob.glob(search_pattern):
            package = Path(match)
            reject_symlink_component(package, base_path, "Package")
            if not package.is_file():
                continue
            if package.suffix.lower() not in _PACKAGE_SUFFIXES:
                continue
            matched_packages.append(package)
        return sorted(matched_packages)
