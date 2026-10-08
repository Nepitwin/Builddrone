"""AppVeyor test results upload module."""

from __future__ import annotations

import mimetypes
import os
import time
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from builddrone.base_module import BaseModule
from builddrone.drone_exception import DroneException
from builddrone.path_safety import reject_symlink_component
from builddrone.runner import Runner


class AppveyorUploadTestsModule(BaseModule):  # pylint: disable=too-few-public-methods
    """Upload JUnit/xUnit XML results files to AppVeyor.

    Blueprint configuration arguments:
        "sources": "Non-empty list of objects with 'file' and 'type'
            ('junit' or 'xunit')"
        "repeat": "Max upload attempts per file (default: 1)"
        "timeout": "Seconds to wait between failed attempts (default: 10)"
    """

    _supported_types = frozenset({"junit", "xunit"})

    def __init__(self) -> None:
        self._upload_url = (
            "https://ci.appveyor.com/api/testresults/{results_type}/{job_id}"
        )
        self._default_repeat = 1
        self._default_timeout = 10
        self._http_timeout = 300

    def run(self, runner: Runner, args: dict) -> None:
        sources = self._require_sources(args)
        repeat = self._parse_positive_int(args, "repeat", self._default_repeat)
        timeout = self._parse_positive_int(args, "timeout", self._default_timeout)
        job_id = self._require_job_id()

        base_path = Path(runner.get_base_path())

        for file_path, results_type in sources:
            source_path = self._resolve_source(file_path, base_path)
            upload_url = self._upload_url.format(
                results_type=results_type,
                job_id=job_id,
            )
            self._upload_with_retry(runner, source_path, upload_url, repeat, timeout)

    def _upload_with_retry(
        self,
        runner: Runner,
        source_path: Path,
        upload_url: str,
        repeat: int,
        timeout: int,
    ) -> None:
        runner.logger.info("Uploading test results to AppVeyor: %s", source_path)

        last_error: Exception | None = None
        for attempt in range(1, repeat + 1):
            try:
                self._upload_file(source_path, upload_url)
                runner.logger.info(
                    "Uploaded test results to AppVeyor (attempt %s/%s): %s",
                    attempt,
                    repeat,
                    source_path,
                )
                return
            except (OSError, HTTPError, URLError) as exc:
                last_error = exc
                runner.logger.error(
                    "AppVeyor upload attempt %s/%s failed for %s: %s",
                    attempt,
                    repeat,
                    source_path,
                    exc,
                )
                if attempt < repeat:
                    runner.logger.info(
                        "Retrying AppVeyor upload in %s seconds...",
                        timeout,
                    )
                    time.sleep(timeout)

        raise DroneException(
            f"Failed to upload test results to AppVeyor after {repeat} attempt(s) "
            f"for {source_path}: {last_error}"
        ) from last_error

    def _require_sources(self, args: dict) -> list[tuple[str, str]]:
        sources = args.get("sources")
        if not isinstance(sources, list) or not sources:
            raise DroneException("Argument 'sources' must be a non-empty list")

        parsed_sources: list[tuple[str, str]] = []
        for source in sources:
            if not isinstance(source, dict):
                raise DroneException(
                    "Argument 'sources' entries must be objects with 'file' and 'type'"
                )

            file_path = source.get("file")
            if not isinstance(file_path, str) or not file_path.strip():
                raise DroneException(
                    "Argument 'sources' object entries require a non-empty 'file'"
                )

            results_type = source.get("type")
            if (
                not isinstance(results_type, str)
                or results_type not in self._supported_types
            ):
                raise DroneException("Argument 'type' must be 'junit' or 'xunit'")

            parsed_sources.append((file_path, results_type))

        return parsed_sources

    @staticmethod
    def _resolve_source(src: str, base_path: Path) -> Path:
        source_path = Path(src)
        if not os.path.isabs(src):
            source_path = base_path / source_path

        reject_symlink_component(source_path, base_path, "Test results file")
        if not source_path.is_file():
            raise DroneException(f"Test results file not found: {source_path}")
        return source_path

    @staticmethod
    def _parse_positive_int(args: dict, name: str, default: int) -> int:
        value = args.get(name, default)
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise DroneException(f"Argument '{name}' must be a positive integer")
        return value

    @staticmethod
    def _require_job_id() -> str:
        job_id = os.environ.get("APPVEYOR_JOB_ID", "").strip()
        if not job_id:
            raise DroneException("Environment variable APPVEYOR_JOB_ID is not set")
        return job_id

    def _upload_file(self, source_path: Path, upload_url: str) -> None:
        boundary = f"----BuilddroneBoundary{uuid.uuid4().hex}"
        filename = source_path.name
        content_type = mimetypes.guess_type(filename)[0] or "application/xml"
        file_bytes = source_path.read_bytes()

        body = b"".join(
            [
                f"--{boundary}\r\n".encode("utf-8"),
                (
                    f'Content-Disposition: form-data; name="file"; '
                    f'filename="{filename}"\r\n'
                ).encode("utf-8"),
                f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"),
                file_bytes,
                b"\r\n",
                f"--{boundary}--\r\n".encode("utf-8"),
            ]
        )

        request = Request(
            upload_url,
            data=body,
            method="POST",
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Content-Length": str(len(body)),
            },
        )

        with urlopen(request, timeout=self._http_timeout) as response:
            response.read()
