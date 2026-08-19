"""Reject paths that cross a symbolic-link component."""

from __future__ import annotations

from pathlib import Path

from builddrone.drone_exception import DroneException


def first_symlink_component(path: Path, base_path: Path) -> Path | None:
    """Return the first symlink on *path* under *base_path*, or None.

    Ancestors of *base_path* are not inspected. If *path* is not located under
    *base_path*, every component after the drive or root is checked instead.
    Missing trailing components are not treated as symlinks.
    """
    try:
        relative = path.relative_to(base_path)
    except ValueError:
        start = Path(path.anchor) if path.anchor else Path()
        parts = path.parts[1:] if path.anchor else path.parts
        return _first_symlink_in_parts(start, parts)

    return _first_symlink_in_parts(base_path, relative.parts)


def reject_symlink_component(path: Path, base_path: Path, kind: str) -> None:
    """Raise DroneException when *path* has a symlink component under *base_path*."""
    found = first_symlink_component(path, base_path)
    if found is not None:
        raise DroneException(f"{kind} must not be a symlink: {found}")


def _first_symlink_in_parts(start: Path, parts: tuple[str, ...]) -> Path | None:
    current = start
    for part in parts:
        current = current / part
        if current.is_symlink():
            return current
        if not current.exists():
            return None
    return None
