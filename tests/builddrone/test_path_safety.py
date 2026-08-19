"""Tests for symlink-component path rejection."""

import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from builddrone.drone_exception import DroneException
from builddrone.path_safety import first_symlink_component, reject_symlink_component


class TestPathSafety(unittest.TestCase):
    """Verify full-path symlink-component detection."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.base_path = Path(self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_first_symlink_component_returns_none_for_regular_file(self):
        """Ignore paths that contain no symlink components."""
        nested = self.base_path / "outer" / "inner"
        nested.mkdir(parents=True)
        file_path = nested / "file.txt"
        file_path.write_text("ok", encoding="utf-8")

        self.assertIsNone(first_symlink_component(file_path, self.base_path))

    def test_first_symlink_component_detects_leaf_symlink(self):
        """Return a file symlink at the leaf."""
        target = self.base_path / "secret.txt"
        target.write_text("secret", encoding="utf-8")
        link_path = self.base_path / "linked.txt"
        try:
            os.symlink(target, link_path)
        except OSError:
            self.skipTest("Cannot create symlinks on this platform")

        self.assertEqual(first_symlink_component(link_path, self.base_path), link_path)

    def test_first_symlink_component_detects_intermediate_directory_symlink(self):
        """Return a directory symlink that appears before the leaf."""
        host_dir = self.base_path / "host"
        host_dir.mkdir()
        (host_dir / "file.txt").write_text("secret", encoding="utf-8")
        link_dir = self.base_path / "outer"
        try:
            os.symlink(host_dir, link_dir, target_is_directory=True)
        except OSError:
            self.skipTest("Cannot create directory symlinks on this platform")

        nested = link_dir / "file.txt"
        self.assertEqual(first_symlink_component(nested, self.base_path), link_dir)

    def test_first_symlink_component_detects_intermediate_when_symlinks_unavailable(
        self,
    ):
        """Return an intermediate path reported as a directory symlink."""
        outer = self.base_path / "outer"
        inner = outer / "inner"
        inner.mkdir(parents=True)
        file_path = inner / "file.txt"
        file_path.write_text("secret", encoding="utf-8")
        original_is_symlink = Path.is_symlink

        def fake_is_symlink(path_self):
            if path_self == outer:
                return True
            return original_is_symlink(path_self)

        with patch.object(Path, "is_symlink", fake_is_symlink):
            self.assertEqual(first_symlink_component(file_path, self.base_path), outer)

    def test_first_symlink_component_ignores_missing_trailing_components(self):
        """Do not treat a missing destination leaf as a symlink."""
        missing = self.base_path / "output" / "archive.zip"
        self.assertIsNone(first_symlink_component(missing, self.base_path))

    def test_reject_symlink_component_raises_with_kind(self):
        """Raise DroneException using the provided kind and symlink path."""
        outer = self.base_path / "outer"
        outer.mkdir()
        file_path = outer / "file.txt"
        file_path.write_text("secret", encoding="utf-8")
        original_is_symlink = Path.is_symlink

        def fake_is_symlink(path_self):
            if path_self == outer:
                return True
            return original_is_symlink(path_self)

        with patch.object(Path, "is_symlink", fake_is_symlink):
            with self.assertRaises(DroneException) as context:
                reject_symlink_component(file_path, self.base_path, "Upload file")

        self.assertEqual(
            str(context.exception),
            f"Upload file must not be a symlink: {outer}",
        )
