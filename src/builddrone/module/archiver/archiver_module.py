"""Archive module for creating zip files from folders and files."""

from __future__ import annotations

import os
import zipfile
from pathlib import Path

from builddrone.base_module import BaseModule
from builddrone.drone_exception import DroneException
from builddrone.runner import Runner


class ArchiverModule(BaseModule):  # pylint: disable=too-few-public-methods
    """Create a zip archive from configured folders and/or files.

    Blueprint configuration arguments:
        "filename": "Destination zip file path"
        "folders": "Optional list of folders to include"
        "files": "Optional list of files to include"
    """

    def run(self, runner: Runner, args: dict) -> None:
        filename = args.get("filename")
        folders = args.get("folders", [])
        files = args.get("files", [])
        base_path = Path(runner.get_base_path())

        if not isinstance(filename, str) or not filename.strip():
            raise DroneException("Argument 'filename' must be a non-empty string")

        if not isinstance(folders, list):
            raise DroneException("Argument 'folders' must be a list")

        if not isinstance(files, list):
            raise DroneException("Argument 'files' must be a list")

        if not folders and not files:
            raise DroneException(
                "At least one of 'folders' or 'files' must be a non-empty list"
            )

        destination = self._resolve_path(filename, base_path)
        destination.parent.mkdir(parents=True, exist_ok=True)

        runner.logger.info("Creating archive: %s", destination)

        try:
            with zipfile.ZipFile(
                destination, "w", compression=zipfile.ZIP_DEFLATED
            ) as archive:
                for folder in folders:
                    self._add_folder(runner, archive, folder, base_path)
                for file_path in files:
                    self._add_file(runner, archive, file_path, base_path)
        except OSError as exc:
            msg = f"Error creating archive {destination}: {exc}"
            runner.logger.error(msg)
            raise DroneException(msg) from exc

        runner.logger.info("Created archive: %s", destination)

    @staticmethod
    def _resolve_path(path: str, base_path: Path) -> Path:
        resolved = Path(path)
        if not os.path.isabs(path):
            resolved = base_path / resolved
        return resolved

    @staticmethod
    def _arcname(path: str, resolved_path: Path, base_path: Path) -> str:
        if not os.path.isabs(path):
            return Path(path).as_posix()
        try:
            return resolved_path.relative_to(base_path).as_posix()
        except ValueError:
            return resolved_path.name

    def _add_folder(
        self,
        runner: Runner,
        archive: zipfile.ZipFile,
        folder: str,
        base_path: Path,
    ) -> None:
        if not isinstance(folder, str) or not folder.strip():
            raise DroneException("Argument 'folders' must contain non-empty strings")

        folder_path = self._resolve_path(folder, base_path)
        if not folder_path.is_dir():
            raise DroneException(f"Folder not found: {folder_path}")

        arc_prefix = self._arcname(folder, folder_path, base_path)
        runner.logger.info("Adding folder to archive: %s", folder_path)

        for root, _, file_names in os.walk(folder_path, followlinks=False):
            for file_name in file_names:
                source_file = Path(root) / file_name
                if source_file.is_symlink():
                    runner.logger.warning("Skipping symlink: %s", source_file)
                    continue
                relative_file = source_file.relative_to(folder_path)
                arcname = str(Path(arc_prefix) / relative_file).replace("\\", "/")
                archive.write(source_file, arcname)

    def _add_file(
        self,
        runner: Runner,
        archive: zipfile.ZipFile,
        file_path: str,
        base_path: Path,
    ) -> None:
        if not isinstance(file_path, str) or not file_path.strip():
            raise DroneException("Argument 'files' must contain non-empty strings")

        source_path = self._resolve_path(file_path, base_path)
        if source_path.is_symlink():
            runner.logger.warning("Skipping symlink: %s", source_path)
            return
        if not source_path.is_file():
            raise DroneException(f"File not found: {source_path}")

        arcname = self._arcname(file_path, source_path, base_path)
        runner.logger.info("Adding file to archive: %s", source_path)
        archive.write(source_path, arcname)
