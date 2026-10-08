"""Shared setup for dotnet module tests."""

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from builddrone.runner import Runner

DOTNET = "dotnet"
WHICH = "builddrone.module.dotnet.dotnet_base_module.shutil.which"


class DotnetModuleTestCase(unittest.TestCase):
    """Create a blueprint directory and a mocked runner.

    ``__test__`` stays false so pytest does not collect this base class.
    Subclasses opt in.
    """

    __test__ = False

    def setUp(self):
        """Create a temporary project file and a mocked runner."""
        self.temp_dir = tempfile.mkdtemp()
        self.base_path = Path(self.temp_dir)
        self.project = self.base_path / "App.csproj"
        self.project.write_text("<Project />\n", encoding="utf-8")
        self.runner = MagicMock(spec=Runner)
        self.runner.logger = MagicMock()
        self.runner.get_base_path.return_value = self.base_path
        self.runner.run_command.return_value = 0

    def tearDown(self):
        """Remove the temporary blueprint directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def assert_command(self, arguments):
        """Assert dotnet ran once with ``arguments`` from the blueprint directory."""
        self.runner.run_command.assert_called_once_with(
            [DOTNET, *arguments],
            cwd=str(self.base_path),
        )
