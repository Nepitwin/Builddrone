"""Execution engine for running builddrone pipeline stages."""

import json

from builddrone.base_module import BaseModule
from builddrone.module.filesystem.cleanup_module import (
    CleanupModule as FilesystemCleanupModule,
)
from builddrone.runner import Runner


class ExecutionEngine:  # pylint: disable=too-few-public-methods
    """Execute configured builddrone stages."""

    def __init__(self, modules: dict[str, BaseModule]):
        """Initialize the execution engine.

        Args:
            modules: Registered builddrone modules.
        """
        self._modules = modules
        self._load_filesystem_modules()
        self._runner = Runner()

    def run(self, config_path: str, stage: str) -> None:
        """Execute a build stage from a configuration file."""
        config = self._load_config(config_path)

        if stage not in config:
            raise ValueError(f"Stage '{stage}' not found in config")

        steps = config[stage]

        for _, step in steps.items():
            self._execute_step(step)

    def _execute_step(self, step: dict) -> None:
        """Execute a single build step."""
        module_name = step.get("module")

        if module_name is None or not isinstance(module_name, str):
            raise ValueError("Unknown module name")

        args = step.get("args", {})
        module = self._modules.get(module_name)

        if module is None:
            raise ValueError(f"Unknown module: {module_name}")

        module.run(self._runner, args)

    def _load_filesystem_modules(self) -> None:
        """Register filesystem modules."""
        self._modules["filesystem.cleanup"] = FilesystemCleanupModule()

    @staticmethod
    def _load_config(path: str) -> dict:
        """Load build configuration from JSON."""
        with open(path, encoding="utf-8") as file:
            return json.load(file)
