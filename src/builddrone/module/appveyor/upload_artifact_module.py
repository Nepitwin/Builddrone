"""AppVeyor artifact upload module."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from builddrone.base_module import BaseModule
from builddrone.drone_exception import DroneException
from builddrone.runner import Runner


class AppveyorUploadArtifactModule(
    BaseModule
):  # pylint: disable=too-few-public-methods
    """Upload build artifacts to AppVeyor using Push-AppveyorArtifact.

    Blueprint configuration arguments:
        "files": "Non-empty list of artifact file paths to upload"
    """

    def run(self, runner: Runner, args: dict) -> None:
        files = self._require_files(args)
        base_path = Path(runner.get_base_path())

        for file_path in files:
            artifact_path = self._resolve_file(file_path, base_path)
            self._upload_artifact(runner, artifact_path)

    @staticmethod
    def _require_files(args: dict) -> list[str]:
        files = args.get("files")
        if not isinstance(files, list) or not files:
            raise DroneException("Argument 'files' must be a non-empty list")

        for file_path in files:
            if not isinstance(file_path, str) or not file_path.strip():
                raise DroneException("Argument 'files' must contain non-empty strings")

        return files

    @staticmethod
    def _resolve_file(path: str, base_path: Path) -> Path:
        artifact_path = Path(path)
        if not os.path.isabs(path):
            artifact_path = base_path / artifact_path

        if not artifact_path.is_file():
            raise DroneException(f"Artifact file not found: {artifact_path}")
        return artifact_path

    @staticmethod
    def _ps_single_quoted(value: str) -> str:
        """Return a PowerShell single-quoted literal safe for -Command strings."""
        return "'" + value.replace("'", "''") + "'"

    @staticmethod
    def _upload_artifact(runner: Runner, artifact_path: Path) -> None:
        artifact_name = artifact_path.name
        path_literal = AppveyorUploadArtifactModule._ps_single_quoted(
            str(artifact_path)
        )
        name_literal = AppveyorUploadArtifactModule._ps_single_quoted(artifact_name)
        command = (
            f"Push-AppveyorArtifact -Path {path_literal} " f"-FileName {name_literal}"
        )
        runner.logger.info("Uploading AppVeyor artifact: %s", artifact_path)

        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", command],
                cwd=str(runner.get_base_path()),
                check=False,
            )
        except OSError as exc:
            msg = f"Failed to upload AppVeyor artifact {artifact_path}: {exc}"
            runner.logger.error(msg)
            raise DroneException(msg) from exc

        if result.returncode != 0:
            raise DroneException(
                f"Failed to upload AppVeyor artifact {artifact_path} "
                f"with exit code {result.returncode}"
            )

        runner.logger.info("Uploaded AppVeyor artifact: %s", artifact_path)
