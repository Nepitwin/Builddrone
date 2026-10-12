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

# Pip opens nested ``-r`` / ``-c`` files and logs ``--find-links`` and ``-e``
# values while parsing a requirements file. Match pip's line splitting so those
# values are checked before pip can echo an expanded secret, or the contents of
# a nested ``file://`` path reached through a remote include, into the build log.
_SCHEME_RE = re.compile(r"^(http|https|file):", re.IGNORECASE)
_VCS_RE = re.compile(r"^(git|hg|svn|bzr)\+", re.IGNORECASE)
_COMMENT_RE = re.compile(r"(^|\s+)#.*$")
_ENV_VAR_RE = re.compile(r"(?P<var>\$\{(?P<name>[A-Z0-9_]+)\})")
_EDITABLE_EXTRAS_RE = re.compile(r"^(?P<path>.+?)(?P<extras>\[[^\]]+\])$")
_OUTSIDE_WORKSPACE = "Requirements reference must exist inside the workspace"
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

        Requirements files are checked before pip runs. Symlink components are
        rejected on the requirements file and on every local ``-r`` and ``-c``
        file pip would open. An expanded ``-r``, ``-c``, ``--find-links``, or
        ``-e`` value that is missing or resolves outside the workspace is
        rejected as well, including a remote requirements URL, so pip cannot
        print it into the build log.

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
        # The blueprint value is passed straight to ``pip install -r``. A remote
        # URL, or a file URL pip would fetch, must be rejected before that, or
        # pip downloads it and opens nested file URLs from the body.
        filename = _local_requirements_argument(requirements, base_path)
        self._reject_requirement_file(filename, base_path, set())

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

        for reference in _iter_references(content, path):
            self._reject_reference(reference, opened, base_path, seen)

    def _reject_reference(
        self,
        reference: tuple[str, str, str],
        parent_filename: str,
        base_path: Path,
        seen: set[str],
    ) -> None:
        kind, original, expanded = reference
        if kind in ("requirement", "constraint"):
            nested = _nested_requirements_path(expanded, parent_filename, base_path)
            if nested is None:
                _raise_outside(original, expanded)
            else:
                self._reject_requirement_file(nested, base_path, seen)
            return

        if kind == "editable":
            target = _editable_target(expanded, base_path)
        else:
            target = _find_links_target(expanded, parent_filename, base_path)
        if not _is_local_workspace_path(target, base_path):
            _raise_outside(original, expanded)


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


def _local_requirements_argument(requirements: str, cwd: Path) -> str:
    """Return a local requirements path, rejecting URLs pip would fetch.

    ``pip install -r https://...`` downloads that file and then opens nested
    ``file://`` paths from it. ``file:///proc/self/environ`` is how that nested
    file prints the process environment into the build log.
    """
    if _is_remote_url(requirements):
        raise DroneException(f"{_OUTSIDE_WORKSPACE}: {requirements}")
    if not _is_file_url(requirements):
        return requirements

    filename = _path_from_file_url(requirements, cwd)
    path = Path(filename)
    try:
        exists = path.is_file()
    except OSError:
        exists = False
    if not exists:
        raise DroneException(f"{_OUTSIDE_WORKSPACE}: {requirements}")
    return filename


def _resolve_include(parent_filename: str, include: str, cwd: Path) -> str:
    """Return the local path pip would open.

    Remote ``http`` and ``https`` includes are refused here. Pip would download
    them and then open nested ``file://`` paths from the downloaded file. The
    local symlink check never sees those nested paths, and pip's error text
    can contain the process environment.
    """
    if _is_remote_url(include):
        raise DroneException(f"{_OUTSIDE_WORKSPACE}: remote requirements include")
    if _is_file_url(include):
        return _path_from_file_url(include, cwd)

    # Match pip: join the parent directory and the include, and do not normpath.
    joined = os.path.join(os.path.dirname(parent_filename), include)
    return _pip_abspath(joined, cwd)


def _path_from_file_url(url: str, cwd: Path) -> str:
    """Return the local path of a ``file:`` URL pip would open.

    A host other than ``localhost`` is not that local path. Pip treats it as a
    UNC path on Windows and rejects it on other platforms, so the workspace
    check would be looking at a different file.
    """
    parts = urllib.parse.urlsplit(url)
    if parts.netloc and parts.netloc.lower() != "localhost":
        raise DroneException(f"{_OUTSIDE_WORKSPACE}: remote requirements include")
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


def _nested_requirements_path(
    value: str, parent_filename: str, base_path: Path
) -> str | None:
    """Return a local requirements path pip may open, or None to reject it.

    Remote ``http`` and ``https`` includes are not downloaded. Pip would fetch
    them and then open nested ``file://`` paths from the downloaded file, and
    the resulting error text can contain the process environment. A local file
    that resolves outside the workspace is rejected the same way, so the
    exception keeps the requirements-file spelling instead of a resolved path.
    """
    try:
        local = _resolve_include(parent_filename, value, base_path)
    except DroneException:
        return None
    path = Path(local)
    try:
        is_file = path.is_file()
    except OSError:
        return None
    if not is_file or not _is_within_workspace(path, base_path):
        return None
    return local


def _find_links_target(value: str, parent_filename: str, cwd: Path) -> Path | None:
    """Return the local find-links path pip would use.

    Pip keeps the original text when the path next to the requirements file
    does not exist, and then logs that text. Missing and remote values therefore
    have no local target.
    """
    if _is_file_url(value):
        return Path(_path_from_file_url(value, cwd))
    if _is_remote_url(value):
        return None

    parent_dir = os.path.dirname(parent_filename)
    relative = os.path.normpath(os.path.join(parent_dir, value))
    if os.path.exists(relative):
        return Path(relative)
    raw = Path(_pip_abspath(value, cwd))
    if raw.exists():
        return raw
    return None


def _editable_target(value: str, cwd: Path) -> Path | None:
    """Return the local editable path pip would use, or None for a URL."""
    if _is_remote_url(value):
        return None
    path_value = value
    extras = _EDITABLE_EXTRAS_RE.match(value)
    if extras is not None:
        path_value = extras.group("path")
    if _is_file_url(path_value):
        candidate = Path(_path_from_file_url(path_value, cwd))
    elif _is_remote_url(path_value):
        return None
    else:
        candidate = Path(_pip_abspath(path_value, cwd))
    try:
        if not candidate.exists():
            return None
    except OSError:
        return None
    return candidate


def _is_file_url(value: str) -> bool:
    return value.lower().startswith("file:")


def _is_remote_url(value: str) -> bool:
    """Return whether *value* is a URL pip would fetch or log as-is."""
    if _is_file_url(value):
        return False
    if _SCHEME_RE.match(value) or _VCS_RE.match(value):
        return True
    return "://" in value


def _is_local_workspace_path(path: Path | None, base_path: Path) -> bool:
    if path is None:
        return False
    try:
        if not path.exists():
            return False
    except OSError:
        return False
    return _is_within_workspace(path, base_path)


def _is_within_workspace(path: Path, base_path: Path) -> bool:
    """Return whether *path* resolves inside *base_path*.

    Symlinks are followed, so a link that leaves the workspace is outside.
    """
    try:
        resolved = os.path.normcase(os.path.realpath(path))
        base = os.path.normcase(os.path.realpath(base_path))
    except (OSError, ValueError):
        return False
    if resolved == base:
        return True
    try:
        return os.path.commonpath([resolved, base]) == base
    except ValueError:
        return False


def _raise_outside(original: str, expanded: str) -> None:
    """Reject a reference without echoing an expanded CI secret."""
    shown = original if original != expanded else expanded
    raise DroneException(f"{_OUTSIDE_WORKSPACE}: {shown}")


def _iter_references(content: str, path: Path):
    """Yield ``(kind, original_value, expanded_value)`` for options pip uses.

    ``original_value`` keeps the requirements-file spelling when an environment
    variable was expanded, so a rejection cannot echo the substituted secret.
    """
    for original, expanded in _preprocess_lines(content):
        expanded_refs = _references_from_line(expanded, path)
        if not expanded_refs:
            continue
        original_refs = _original_references(original, expanded, expanded_refs, path)
        for index, (kind, expanded_value) in enumerate(expanded_refs):
            original_value = expanded_value
            if index < len(original_refs) and original_refs[index][0] == kind:
                original_value = original_refs[index][1]
            elif original != expanded:
                original_value = original
            yield kind, original_value, expanded_value


def _original_references(
    original: str,
    expanded: str,
    expanded_refs: list[tuple[str, str]],
    path: Path,
) -> list[tuple[str, str]]:
    if original == expanded:
        return expanded_refs
    try:
        return _references_from_line(original, path)
    except DroneException:
        return []


def _preprocess_lines(content: str):
    """Yield ``(original, expanded)`` lines the way pip splits them."""
    lines = _join_lines(content.splitlines())
    for line in lines:
        stripped = _COMMENT_RE.sub("", line).strip()
        if stripped:
            yield stripped, _expand_env_variables(stripped)


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


def _references_from_line(line: str, path: Path) -> list[tuple[str, str]]:
    """Return ``-e``, ``-r``, ``-c``, and ``--find-links`` values pip would use.

    A package line such as ``build -r secret.txt`` is ignored. Pip only acts on
    these options when the line has no requirement argument.
    """
    args, options_str = _break_args_options(line)
    if args:
        return []

    try:
        tokens = shlex.split(options_str)
    except ValueError:
        raise DroneException(f"Could not parse requirements file: {path}") from None

    parser = _build_requirement_parser()
    try:
        opts, _unused = parser.parse_args(tokens)
    except _OptionParsingError:
        raise DroneException(f"Could not parse requirements file: {path}") from None

    references: list[tuple[str, str]] = []
    for value in opts.editables or []:
        references.append(("editable", value))
    for value in opts.requirements or []:
        references.append(("requirement", value))
    for value in opts.constraints or []:
        references.append(("constraint", value))
    for value in opts.find_links or []:
        references.append(("find-links", value))
    return references


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
