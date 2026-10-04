"""Guard setuptools discovery against planted auto-imported packages."""

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
PYPROJECT = REPO_ROOT / "pyproject.toml"
FORBIDDEN_AUTOIMPORTS = ("sitecustomize", "usercustomize")


class TestPackageLayout(unittest.TestCase):
    """Verify only builddrone is discoverable as a top-level package."""

    def test_pyproject_limits_setuptools_package_find(self):
        """Package discovery must not install every directory under src/."""
        text = PYPROJECT.read_text(encoding="utf-8")
        self.assertIn("[tool.setuptools.packages.find]", text)
        self.assertIn('where = ["src"]', text)
        self.assertIn('include = ["builddrone*"]', text)

    def test_src_top_level_is_only_builddrone(self):
        """Refuse extra top-level packages that pip install . would ship."""
        unexpected = []
        for entry in sorted(SRC_ROOT.iterdir()):
            if entry.name.endswith(".egg-info"):
                continue
            if entry.is_dir() or entry.name.endswith(".py"):
                if entry.name != "builddrone":
                    unexpected.append(entry.name)
        self.assertEqual(unexpected, [])

    def test_sitecustomize_is_not_planted_at_import_roots(self):
        """sitecustomize/usercustomize at cwd or src/ would auto-import in CI."""
        planted = []
        for name in FORBIDDEN_AUTOIMPORTS:
            for candidate in (
                REPO_ROOT / name,
                REPO_ROOT / f"{name}.py",
                SRC_ROOT / name,
                SRC_ROOT / f"{name}.py",
            ):
                if candidate.exists():
                    planted.append(str(candidate.relative_to(REPO_ROOT)))
        self.assertEqual(planted, [])
