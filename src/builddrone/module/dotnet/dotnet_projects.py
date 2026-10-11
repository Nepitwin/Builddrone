"""Locate projects and the package files ``dotnet pack`` writes."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from xml.etree import ElementTree

from builddrone.drone_exception import DroneException
from builddrone.path_safety import reject_symlink_component

_PROJECT_SUFFIXES = {".csproj", ".fsproj", ".vbproj"}
_SOLUTION_SUFFIXES = {".sln", ".slnx", ".slnf"}
_ENTRY_SUFFIXES = _PROJECT_SUFFIXES | _SOLUTION_SUFFIXES
_MAX_IMPORT_DEPTH = 10
_VERSION = re.compile(
    r"^(?P<major>\d+)"
    r"(?:\.(?P<minor>\d+))?"
    r"(?:\.(?P<patch>\d+))?"
    r"(?:\.(?P<revision>\d+))?"
    r"(?P<release>-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
_SLN_PROJECT_LINE = re.compile(
    r'^\s*Project\("\{[0-9A-Fa-f-]+\}"\)\s*=\s*"[^"]*"\s*,\s*'
    r'"(?P<path>[^"]+)"\s*,\s*"\{[0-9A-Fa-f-]+\}"'
)
_PROPERTY_REF = re.compile(r"\$\(([^)]+)\)")


def selected_project_files(target: str | None, base_path: Path) -> list[Path]:
    """Return project files selected by ``target`` or discovered in ``base_path``."""
    if target is None:
        entry = _discover_entry(base_path)
        if entry is None:
            return []
    else:
        entry = Path(target)

    reject_symlink_component(entry, base_path, "Project")
    projects = _expand_projects(entry)
    for project in projects:
        if project != entry:
            reject_symlink_component(project, base_path, "Project")
    return projects


def package_paths(
    project: Path,
    output_directory: Path | None,
    configuration: str,
    version_suffix: str | None,
    include_symbols: bool,
) -> list[Path]:
    """Return the nupkg path, and both symbol-package names when symbols are on.

    ``dotnet pack`` follows an existing file at
    ``{PackageId}.{Version}.nupkg``. With ``--include-symbols`` it also writes
    either ``.snupkg`` or ``.symbols.nupkg``. The SDK default is
    ``symbols.nupkg`` unless ``SymbolPackageFormat`` is ``snupkg``. Both names
    are checked so a planted symlink is not followed.
    """
    if not project.is_file():
        raise DroneException(f"Project not found: {project}")

    props = _properties(project)
    _set_prop(props, "Configuration", configuration)
    if version_suffix is not None:
        _set_prop(props, "VersionSuffix", version_suffix)
    _set_prop(props, "MSBuildProjectName", project.stem)
    if _get_prop(props, "AssemblyName") is None:
        _set_prop(props, "AssemblyName", "$(MSBuildProjectName)")
    props = _expand(props)

    if _is_false(_get_prop(props, "IsPackable")):
        return []

    package_id = _get_prop(props, "PackageId") or _get_prop(props, "AssemblyName")
    if not package_id:
        package_id = project.stem
    version = _package_version(props)
    output_dir = (
        output_directory
        if output_directory is not None
        else _default_package_directory(project, props, configuration)
    )
    packages = [output_dir / f"{package_id}.{version}.nupkg"]
    if include_symbols:
        packages.append(output_dir / f"{package_id}.{version}.snupkg")
        packages.append(output_dir / f"{package_id}.{version}.symbols.nupkg")
    return packages


def _discover_entry(directory: Path) -> Path | None:
    """Return the only project or solution directly inside ``directory``."""
    if not directory.is_dir():
        return None
    entries = [
        path
        for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() in _ENTRY_SUFFIXES
    ]
    if len(entries) == 1:
        return entries[0]
    return None


def _expand_projects(target: Path) -> list[Path]:
    if target.is_dir():
        entry = _discover_entry(target)
        return [] if entry is None else _expand_projects(entry)

    suffix = target.suffix.lower()
    if suffix in _PROJECT_SUFFIXES:
        return [target]
    readers = {
        ".slnx": _projects_from_slnx,
        ".sln": _projects_from_sln,
        ".slnf": _projects_from_slnf,
    }
    reader = readers.get(suffix)
    if reader is None:
        return []
    return reader(target)


def _projects_from_slnx(path: Path) -> list[Path]:
    root = _parse_xml(path, "solution")
    projects: list[Path] = []
    for element in root.iter():
        if _local_name(element.tag) != "Project":
            continue
        project_path = element.attrib.get("Path")
        if not project_path:
            continue
        candidate = _relative_to(path.parent, project_path)
        if candidate.suffix.lower() in _PROJECT_SUFFIXES:
            projects.append(candidate)
    return projects


def _projects_from_sln(path: Path) -> list[Path]:
    try:
        text = _read_text(path)
    except OSError as exc:
        raise DroneException(f"Cannot read solution: {path}") from exc

    projects: list[Path] = []
    for match in _SLN_PROJECT_LINE.finditer(text):
        candidate = _relative_to(path.parent, match.group("path"))
        if candidate.suffix.lower() in _PROJECT_SUFFIXES:
            projects.append(candidate)
    return projects


def _projects_from_slnf(path: Path) -> list[Path]:
    try:
        data = json.loads(_read_text(path))
        solution = data["solution"]
        solution_path = solution["path"]
        listed = solution["projects"]
    except (OSError, json.JSONDecodeError, UnicodeError, KeyError, TypeError) as exc:
        raise DroneException(f"Cannot read solution: {path}") from exc

    if not isinstance(solution_path, str) or not isinstance(listed, list):
        raise DroneException(f"Cannot read solution: {path}")

    solution_dir = _relative_to(path.parent, solution_path).parent
    projects: list[Path] = []
    for project_path in listed:
        if not isinstance(project_path, str):
            raise DroneException(f"Cannot read solution: {path}")
        candidate = _relative_to(solution_dir, project_path)
        if candidate.suffix.lower() in _PROJECT_SUFFIXES:
            projects.append(candidate)
    return projects


def _properties(project: Path) -> dict[str, str]:
    """Return unconditional properties, including directory build imports."""
    props: dict[str, str] = {}
    seen: set[str] = set()
    directory_props = _file_above(project.parent, "Directory.Build.props")
    if directory_props is not None:
        _apply_msbuild_file(props, directory_props, seen, 0)
    _apply_msbuild_file(props, project, seen, 0)
    directory_targets = _file_above(project.parent, "Directory.Build.targets")
    if directory_targets is not None:
        _apply_msbuild_file(props, directory_targets, seen, 0)
    return props


def _apply_msbuild_file(
    props: dict[str, str], path: Path, seen: set[str], depth: int
) -> None:
    key = os.path.normcase(str(path))
    if key in seen or depth > _MAX_IMPORT_DEPTH:
        return
    seen.add(key)

    root = _parse_xml(path, "project file")
    for child in list(root):
        name = _local_name(child.tag)
        if name == "PropertyGroup":
            _apply_property_group(props, child)
        elif name == "Import":
            _apply_import(props, path, child, seen, depth)


def _apply_property_group(props: dict[str, str], group: ElementTree.Element) -> None:
    if group.attrib.get("Condition"):
        return
    for child in list(group):
        if child.attrib.get("Condition"):
            continue
        text = (child.text or "").strip()
        _set_prop(props, _local_name(child.tag), text)


def _apply_import(
    props: dict[str, str],
    owner: Path,
    element: ElementTree.Element,
    seen: set[str],
    depth: int,
) -> None:
    if element.attrib.get("Condition"):
        return
    project = element.attrib.get("Project")
    if not project or "$(" in project:
        return
    imported = _relative_to(owner.parent, project)
    if not imported.is_file():
        return
    _apply_msbuild_file(props, imported, seen, depth + 1)


def _file_above(start: Path, name: str) -> Path | None:
    current = start
    while True:
        candidate = current / name
        if candidate.is_file():
            return candidate
        parent = current.parent
        if parent == current:
            return None
        current = parent


def _default_package_directory(
    project: Path, props: dict[str, str], configuration: str
) -> Path:
    package_output = _get_prop(props, "PackageOutputPath")
    if package_output:
        return _relative_to(project.parent, package_output)
    base_output = _get_prop(props, "BaseOutputPath") or "bin"
    return _relative_to(project.parent, base_output) / configuration


def _package_version(props: dict[str, str]) -> str:
    """Return the normalized package version ``dotnet pack`` puts in the file name."""
    explicit = _get_prop(props, "PackageVersion") or _get_prop(props, "Version")
    if explicit:
        return _normalize_nuget_version(explicit)
    prefix = _get_prop(props, "VersionPrefix") or "1.0.0"
    suffix = _get_prop(props, "VersionSuffix")
    version = f"{prefix}-{suffix}" if suffix else prefix
    return _normalize_nuget_version(version)


def _normalize_nuget_version(version: str) -> str:
    """Match NuGet's package file name, including ``1.2`` becoming ``1.2.0``."""
    normalized = version.strip().split("+", 1)[0].strip()
    match = _VERSION.fullmatch(normalized)
    if match is None:
        return normalized or "1.0.0"

    major = match.group("major")
    minor = match.group("minor") or "0"
    patch = match.group("patch") or "0"
    revision = match.group("revision")
    release = match.group("release") or ""
    if revision and int(revision) != 0:
        core = f"{major}.{minor}.{patch}.{revision}"
    else:
        core = f"{major}.{minor}.{patch}"
    return f"{core}{release}"


def _expand(props: dict[str, str]) -> dict[str, str]:
    expanded = dict(props)
    for _ in range(10):
        changed = False
        for key, value in list(expanded.items()):
            updated = _PROPERTY_REF.sub(
                lambda match, bag=expanded: _lookup(bag, match.group(1)),
                value,
            )
            if updated != value:
                expanded[key] = updated
                changed = True
        if not changed:
            return expanded
    return expanded


def _set_prop(props: dict[str, str], name: str, value: str) -> None:
    for existing in list(props):
        if existing.lower() == name.lower():
            del props[existing]
    if value:
        props[name] = value


def _get_prop(props: dict[str, str], name: str) -> str | None:
    for key, value in props.items():
        if key.lower() == name.lower() and value:
            return value
    return None


def _lookup(props: dict[str, str], name: str) -> str:
    return _get_prop(props, name) or ""


def _is_false(value: str | None) -> bool:
    return value is not None and value.strip().lower() == "false"


def _parse_xml(path: Path, kind: str) -> ElementTree.Element:
    try:
        return ElementTree.parse(path).getroot()
    except (ElementTree.ParseError, OSError) as exc:
        raise DroneException(f"Cannot read {kind}: {path}") from exc


def _read_text(path: Path) -> str:
    raw = path.read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16")
    return raw.decode("utf-8-sig")


def _relative_to(base: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return base / path


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]
