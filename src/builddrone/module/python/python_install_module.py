"""Python install module."""

from __future__ import annotations

import codecs
import locale
import optparse
import os
import re
import shlex
import urllib.parse
import urllib.request
from pathlib import Path

from builddrone.base_module import BaseModule
from builddrone.drone_exception import DroneException
from builddrone.path_safety import reject_symlink_component
from builddrone.runner import Runner

# Pip opens nested ``-r`` / ``-c`` files while parsing a requirements file.
# Match the line splitting in pip's requirements parser so every local file
# it would open is checked before pip can echo a failed line into the log.
_SCHEME_RE = re.compile(r"^(http|https|file):", re.IGNORECASE)
_COMMENT_RE = re.compile(r"(^|\s+)#.*$")
_ENV_VAR_RE = re.compile(r"(?P<var>\$\{(?P<name>[A-Z0-9_]+)\})")
_PEP263_ENCODING_RE = re.compile(rb"coding[:=]\s*([-\w.]+)")
_BOMS = (
    (codecs.BOM_UTF8, "utf-8"),
    (codecs.BOM_UTF32, "utf-32"),
    (codecs.BOM_UTF32_BE, "utf-32-be"),
    (codecs.BOM_UTF32_LE, "utf-32-le"),
    (codecs.BOM_UTF16, "utf-16"),
    (codecs.BOM_UTF16_BE, "utf-16-be"),
    (codecs.BOM_UTF16_LE, "utf-16-le"),
)


class _OptionParsingError(Exception):
    """A requirements-file option line could not be parsed."""


class _RequirementParser(optparse.OptionParser):
    """Option parser that raises instead of exiting the process."""

    def error(self, msg: str) -> None:
        raise _OptionParsingError(msg)


class PythonInstallModule(BaseModule):  # pylint: disable=too-few-public-methods
    """A module responsible for installing Python packages.

    Blueprint configuration arguments:
        "source": "Package source to install"
        "requirements": "Requirements file to install"
    """

    def run(self, runner: Runner, args: dict) -> None:
        """Install a package source with ``python -m pip install``.

        ``--disable-pip-version-check`` suppresses pip upgrade notices that
        otherwise go to stderr and fail PowerShell/AppVeyor hosts.

        Requirements files are checked for symlink components, including every
        local ``-r`` and ``-c`` file pip would open, before pip runs. The path
        pip opens is kept intact, so a ``..`` segment cannot hide an earlier
        symlink, and an include that resolves outside the workspace is rejected.

        Args:
            runner: Runner instance used to execute commands.
            args: Module configuration arguments.
        """
        runner.logger.info("Installing...")
        source = args.get("source")
        requirements = args.get("requirements")
        base_path = Path(runner.get_base_path())

        if isinstance(requirements, str) and requirements:
            self._reject_requirements(requirements, base_path)
            install_args = ["-r", requirements]
        elif isinstance(source, str) and source:
            source_path = self._resolve_path(source, base_path)
            reject_symlink_component(source_path, base_path, "Install source")
            install_args = [source]
        else:
            raise DroneException("No source or requirements provided for install")

        exit_code = runner.run(
            ["-m", "pip", "install", "--disable-pip-version-check", *install_args],
            cwd=str(base_path),
        )

        if exit_code != 0:
            raise DroneException(f"Install failed with exit code {exit_code}")

    @staticmethod
    def _resolve_path(path: str, base_path: Path) -> Path:
        resolved = Path(path)
        if not os.path.isabs(path):
            resolved = base_path / resolved
        return resolved

    def _reject_requirements(self, requirements: str, base_path: Path) -> None:
        seen: set[str] = set()
        self._reject_requirement_file(requirements, base_path, seen)

    def _reject_requirement_file(
        self, filename: str, base_path: Path, seen: set[str]
    ) -> None:
        opened = _pip_abspath(filename, base_path)
        path = Path(opened)
        # Pip joins nested includes and passes that string to open(). Collapsing
        # ".." first would hide a symlink such as escape/../environ.
        reject_symlink_component(path, base_path, "Requirements file")
        resolved = _require_inside_workspace(path, base_path)
        key = os.path.normcase(str(resolved))
        if key in seen:
            return
        seen.add(key)

        if not path.is_file():
            return

        try:
            content = _read_requirements(path)
        except (OSError, UnicodeError, LookupError):
            raise DroneException(f"Could not read requirements file: {path}") from None

        for include in _iter_includes(content, path):
            nested = _resolve_include(opened, include, base_path)
            if nested is None:
                continue
            self._reject_requirement_file(nested, base_path, seen)


def _pip_abspath(filename: str, cwd: Path) -> str:
    """Return the path pip opens, without collapsing ``..``."""
    if os.path.isabs(filename):
        return filename
    return os.path.join(str(cwd), filename)


def _require_inside_workspace(path: Path, base_path: Path) -> Path:
    """Return *path* resolved, or raise when that location leaves the workspace.

    Resolution follows symlinks the way ``open`` does, so ``..`` after a link
    is applied to the link target rather than the lexical parent.
    """
    try:
        resolved = path.resolve()
        root = base_path.resolve()
    except (OSError, RuntimeError):
        raise DroneException(f"Could not read requirements file: {path}") from None

    try:
        resolved.relative_to(root)
    except ValueError:
        raise DroneException(
            f"Requirements file resolves outside the workspace: {resolved}"
        ) from None
    return resolved


def _resolve_include(parent_filename: str, include: str, cwd: Path) -> str | None:
    """Return the local path pip would open, or None for a remote include."""
    if _SCHEME_RE.match(include):
        if not include.lower().startswith("file:"):
            return None
        return _path_from_file_url(include, cwd)

    # Match pip: join the parent directory and the include, and do not normpath.
    joined = os.path.join(os.path.dirname(parent_filename), include)
    return _pip_abspath(joined, cwd)


def _path_from_file_url(url: str, cwd: Path) -> str:
    parts = urllib.parse.urlsplit(url)
    path = urllib.request.url2pathname(parts.path)
    if os.path.isabs(path):
        return path
    return _pip_abspath(path, cwd)


def _read_requirements(path: Path) -> str:
    data = path.read_bytes()
    for bom, encoding in _BOMS:
        if data.startswith(bom):
            return data[len(bom) :].decode(encoding)

    for line in data.split(b"\n")[:2]:
        if line.startswith(b"#"):
            match = _PEP263_ENCODING_RE.search(line)
            if match is not None:
                encoding = match.group(1).decode("ascii")
                return data.decode(encoding)

    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        encoding = locale.getpreferredencoding(False) or "utf-8"
        return data.decode(encoding)


def _iter_includes(content: str, path: Path):
    for line in _preprocess_lines(content):
        include = _include_from_line(line, path)
        if include is not None:
            yield include


def _preprocess_lines(content: str):
    lines = _join_lines(content.splitlines())
    for line in lines:
        stripped = _COMMENT_RE.sub("", line).strip()
        if stripped:
            yield _expand_env_variables(stripped)


def _join_lines(lines: list[str]) -> list[str]:
    """Join continuation lines the way pip does."""
    joined: list[str] = []
    pending: list[str] = []
    for line in lines:
        if not line.endswith("\\") or _COMMENT_RE.match(line):
            continued = f" {line}" if _COMMENT_RE.match(line) else line
            if pending:
                pending.append(continued)
                joined.append("".join(pending))
                pending = []
            else:
                joined.append(continued)
            continue
        pending.append(line.strip("\\"))

    if pending:
        joined.append("".join(pending))
    return joined


def _expand_env_variables(line: str) -> str:
    for env_var, var_name in _ENV_VAR_RE.findall(line):
        value = os.getenv(var_name)
        if not value:
            continue
        line = line.replace(env_var, value)
    return line


def _include_from_line(line: str, path: Path) -> str | None:
    """Return the first local ``-r`` or ``-c`` path on an option-only line."""
    _args, options_str = _break_args_options(line)
    if _args:
        return None

    try:
        tokens = shlex.split(options_str)
    except ValueError:
        raise DroneException(f"Could not parse requirements file: {path}") from None

    parser = _build_requirement_parser()
    try:
        opts, _unused = parser.parse_args(tokens)
    except _OptionParsingError:
        raise DroneException(f"Could not parse requirements file: {path}") from None

    if opts.requirements:
        return opts.requirements[0]
    if opts.constraints:
        return opts.constraints[0]
    return None


def _break_args_options(line: str) -> tuple[str, str]:
    tokens = line.split(" ")
    args: list[str] = []
    options = tokens[:]
    for token in tokens:
        if token.startswith(("-", "--")):
            break
        args.append(token)
        options.pop(0)
    return " ".join(args), " ".join(options)


def _build_requirement_parser() -> _RequirementParser:
    parser = _RequirementParser(add_help_option=False)
    parser.add_option("-i", "--index-url", "--pypi-url", dest="index_url")
    parser.add_option("--extra-index-url", dest="extra_index_urls", action="append")
    parser.add_option("--no-index", dest="no_index", action="store_true")
    parser.add_option("-c", "--constraint", dest="constraints", action="append")
    parser.add_option("-r", "--requirement", dest="requirements", action="append")
    parser.add_option("-e", "--editable", dest="editables", action="append")
    parser.add_option("-f", "--find-links", dest="find_links", action="append")
    parser.add_option("--no-binary", dest="no_binary")
    parser.add_option("--only-binary", dest="only_binary")
    parser.add_option("--prefer-binary", dest="prefer_binary", action="store_true")
    parser.add_option("--require-hashes", dest="require_hashes", action="store_true")
    parser.add_option("--pre", dest="pre", action="store_true")
    parser.add_option("--trusted-host", dest="trusted_hosts", action="append")
    parser.add_option("--use-feature", dest="features_enabled", action="append")
    parser.add_option("--global-option", dest="global_options", action="append")
    parser.add_option("--hash", dest="hashes", action="append")
    parser.add_option(
        "-C", "--config-settings", dest="config_settings", action="append"
    )
    return parser
