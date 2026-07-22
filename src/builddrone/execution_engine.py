"""Execution engine for running builddrone pipeline stages."""

import json
from pathlib import Path

from builddrone.base_module import BaseModule
from builddrone.drone_exception import DroneException
from builddrone.module.filesystem.cleanup_module import (
    CleanupModule as FilesystemCleanupModule,
)
from builddrone.module.filesystem.copy_module import FilesystemCopyModule
from builddrone.module.python.build_module import PythonBuildModule
from builddrone.module.python.install_module import PythonInstallModule
from builddrone.module.python.pylint_module import PylintModule
from builddrone.module.python.run_module import PythonRunModule
from builddrone.module.python.venv_module import PythonVirtualEnvironmentModule
from builddrone.module.robotframework.rebot_module import RobotframeworkRebotModule
from builddrone.module.robotframework.test_module import RobotframeworkTestModule
from builddrone.runner import Runner


class ExecutionEngine:  # pylint: disable=too-few-public-methods
    """Execute configured builddrone stages."""

    def __init__(self, modules: dict[str, BaseModule]):
        """Initialize the execution engine.

        Args:
            modules: Registered builddrone modules.
        """
        self._modules = modules
        self._config_path = Path("blueprint.json")
        self._register_module("filesystem.cleanup", FilesystemCleanupModule())
        self._register_module("filesystem.copy", FilesystemCopyModule())
        self._register_module("python.build", PythonBuildModule())
        self._register_module("python.install", PythonInstallModule())
        self._register_module("python.run", PythonRunModule())
        self._register_module("python.venv", PythonVirtualEnvironmentModule())
        self._register_module("python.pylint", PylintModule())
        self._register_module("robotframework.test", RobotframeworkTestModule())
        self._register_module("robotframework.rebot", RobotframeworkRebotModule())
        self._runner = Runner()

    def run(self, stage: str) -> None:
        """Execute a build stage from a configuration file."""
        config_path = self._config_path
        config_file = config_path.resolve()
        self._runner.set_base_path(config_file.parent)
        config = self._load_config(str(config_path))

        if stage not in config:
            raise DroneException(f"Stage '{stage}' not found in config")

        steps = config[stage]

        if not isinstance(steps, list):
            raise DroneException(f"Stage '{stage}' must be a list of steps")

        for step in steps:
            self._execute_step(step)

    def _execute_step(self, step: dict) -> None:
        """Execute a single build step."""
        if not isinstance(step, dict):
            raise DroneException("Pipeline step must be an object")

        module_name = step.get("module")

        if module_name is None or not isinstance(module_name, str):
            raise DroneException("Unknown module name")

        args = step.get("args", {})
        module = self._modules.get(module_name)

        if module is None:
            raise DroneException(f"Unknown module: {module_name}")

        module.run(self._runner, args)

    def _register_module(self, name: str, module: BaseModule) -> None:
        """Register a single build module."""
        if name not in self._modules:
            self._modules[name] = module

    @staticmethod
    def _load_config(path: str) -> dict:
        """Load build configuration from JSON."""
        with open(path, encoding="utf-8") as file:
            return json.load(file)
