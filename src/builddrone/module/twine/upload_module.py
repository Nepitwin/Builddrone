"""Twine upload module."""

from __future__ import annotations

import glob
import os
from pathlib import Path

from builddrone.base_module import BaseModule
from builddrone.drone_exception import DroneException
from builddrone.runner import Runner


class TwineUploadModule(BaseModule):  # pylint: disable=too-few-public-methods
    """Upload distribution files to a package index with twine.

    Blueprint configuration arguments:
        "files": "Non-empty list of glob patterns selecting files to upload"
        "skip_existing": "Skip files that already exist on the index (default: true)"
        "repository": "Optional upload URL passed to twine --repository-url"
    """

    def run(self, runner: Runner, args: dict) -> None:
        files = self._require_files(args)
        skip_existing = self._require_skip_existing(args)
        repository = args.get("repository")
        base_path = Path(runner.get_base_path())

        if repository is not None and (
            not isinstance(repository, str) or not repository.strip()
        ):
            raise DroneException("Argument 'repository' must be a non-empty string")

        self._ensure_twine_installed(runner)

        for pattern in files:
            matched_files = self._resolve_glob(pattern, base_path)
            if not matched_files:
                raise DroneException(f"No files matched pattern: {pattern}")

            command = ["-m", "twine", "upload"]
            if skip_existing:
                command.append("--skip-existing")
            if repository:
                command.extend(["--repository-url", repository])
            command.extend(str(file_path) for file_path in matched_files)

            runner.logger.info(
                "Uploading files matching %s: %s",
                pattern,
                ", ".join(file_path.name for file_path in matched_files),
            )
            exit_code = runner.run(command, cwd=str(base_path))

            if exit_code != 0:
                raise DroneException(
                    f"Twine upload failed for pattern '{pattern}' "
                    f"with exit code {exit_code}"
                )

    @staticmethod
    def _require_files(args: dict) -> list[str]:
        files = args.get("files")
        if not isinstance(files, list) or not files:
            raise DroneException("Argument 'files' must be a non-empty list")

        for file_pattern in files:
            if not isinstance(file_pattern, str) or not file_pattern.strip():
                raise DroneException("Argument 'files' must contain non-empty strings")

        return files

    @staticmethod
    def _require_skip_existing(args: dict) -> bool:
        skip_existing = args.get("skip_existing", True)
        if not isinstance(skip_existing, bool):
            raise DroneException("Argument 'skip_existing' must be a boolean")
        return skip_existing

    @staticmethod
    def _resolve_glob(pattern: str, base_path: Path) -> list[Path]:
        search_pattern = pattern
        if not os.path.isabs(pattern):
            search_pattern = str(base_path / pattern)

        matched_files = [
            Path(match) for match in glob.glob(search_pattern) if Path(match).is_file()
        ]
        return sorted(matched_files)

    @staticmethod
    def _ensure_twine_installed(runner: Runner) -> None:
        exit_code = runner.run(
            ["-m", "twine", "--version"],
            cwd=str(runner.get_base_path()),
        )
        if exit_code != 0:
            raise DroneException("twine is not installed")
