"""Tests for the Builddrone execution engine."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import DEFAULT, MagicMock, patch

from builddrone.drone_exception import DroneException
from builddrone.execution_engine import ExecutionEngine


class TestExecutionEngine(unittest.TestCase):
    """Verify engine wiring and stage dispatch."""

    def test_init_registers_internal_modules(self):
        """Initialization should register built-in modules."""
        runner_instance = MagicMock()
        instances = {
            "FilesystemCleanupModule": MagicMock(),
            "FilesystemCopyModule": MagicMock(),
            "PylintModule": MagicMock(),
            "RobotframeworkRebotModule": MagicMock(),
            "RobotframeworkTestModule": MagicMock(),
            "PythonRunModule": MagicMock(),
            "PythonInstallModule": MagicMock(),
            "PythonBuildModule": MagicMock(),
            "PythonVirtualEnvironmentModule": MagicMock(),
        }

        with patch.multiple(
            "builddrone.execution_engine",
            FilesystemCleanupModule=DEFAULT,
            FilesystemCopyModule=DEFAULT,
            PylintModule=DEFAULT,
            RobotframeworkRebotModule=DEFAULT,
            RobotframeworkTestModule=DEFAULT,
            PythonRunModule=DEFAULT,
            PythonInstallModule=DEFAULT,
            PythonBuildModule=DEFAULT,
            PythonVirtualEnvironmentModule=DEFAULT,
            Runner=DEFAULT,
        ) as mocks:
            for name, instance in instances.items():
                mocks[name].return_value = instance

            mocks["Runner"].return_value = runner_instance

            modules = {"custom": MagicMock()}
            ExecutionEngine(modules)

        mocks["Runner"].assert_called_once_with()
        self.assertIs(
            modules["filesystem.cleanup"], instances["FilesystemCleanupModule"]
        )
        self.assertIs(modules["filesystem.copy"], instances["FilesystemCopyModule"])
        self.assertIs(modules["python.build"], instances["PythonBuildModule"])
        self.assertIs(modules["python.install"], instances["PythonInstallModule"])
        self.assertIs(modules["python.run"], instances["PythonRunModule"])
        self.assertIs(
            modules["python.venv"], instances["PythonVirtualEnvironmentModule"]
        )
        self.assertIs(
            modules["robotframework.test"], instances["RobotframeworkTestModule"]
        )
        self.assertIs(modules["python.pylint"], instances["PylintModule"])
        self.assertIs(
            modules["robotframework.rebot"], instances["RobotframeworkRebotModule"]
        )
        self.assertIn("custom", modules)

    @patch("builddrone.execution_engine.Runner")
    @patch.object(ExecutionEngine, "_load_config", return_value={"build": {}})
    def test_run_raises_when_stage_is_missing(self, mock_load_config, mock_runner):
        """run should fail when the requested stage is absent."""
        mock_runner.return_value = MagicMock()
        engine = ExecutionEngine({})

        with self.assertRaises(DroneException) as context:
            engine.run("release")

        mock_load_config.assert_called_once_with("blueprint.json")
        self.assertEqual(str(context.exception), "Stage 'release' not found in config")

    @patch("builddrone.execution_engine.Runner")
    @patch.object(
        ExecutionEngine,
        "_load_config",
        return_value={
            "build": {
                "first": {"module": "custom", "args": {"name": "first"}},
                "second": {"module": "custom", "args": {"name": "second"}},
            }
        },
    )
    def test_run_executes_steps_in_order(self, mock_load_config, mock_runner):
        """run should execute each step in the configured order."""
        custom_module = MagicMock()
        runner_instance = MagicMock()
        mock_runner.return_value = runner_instance
        modules = {"custom": custom_module}
        engine = ExecutionEngine(modules)

        engine.run("build")

        self.assertEqual(custom_module.run.call_count, 2)
        custom_module.run.assert_any_call(runner_instance, {"name": "first"})
        custom_module.run.assert_any_call(runner_instance, {"name": "second"})
        mock_load_config.assert_called_once_with("blueprint.json")

    @patch("builddrone.execution_engine.Runner")
    @patch.object(
        ExecutionEngine,
        "_load_config",
        return_value={"build": {"step": {"args": {}}}},
    )
    def test_run_rejects_unknown_module_name(self, mock_load_config, mock_runner):
        """run should reject steps that omit a module name."""
        mock_runner.return_value = MagicMock()
        engine = ExecutionEngine({})

        with self.assertRaises(DroneException) as context:
            engine.run("build")

        mock_load_config.assert_called_once_with("blueprint.json")
        self.assertEqual(str(context.exception), "Unknown module name")

    @patch("builddrone.execution_engine.Runner")
    @patch.object(
        ExecutionEngine,
        "_load_config",
        return_value={"build": {"step": {"module": "missing", "args": {}}}},
    )
    def test_run_rejects_unregistered_module(self, mock_load_config, mock_runner):
        """run should reject steps that reference unknown modules."""
        mock_runner.return_value = MagicMock()
        engine = ExecutionEngine({})

        with self.assertRaises(DroneException) as context:
            engine.run("build")

        mock_load_config.assert_called_once_with("blueprint.json")
        self.assertEqual(str(context.exception), "Unknown module: missing")

    @patch("builddrone.execution_engine.Runner")
    @patch("builddrone.execution_engine.json.load")
    def test_run_loads_json_config(self, mock_json_load, mock_runner):
        """run should deserialize the JSON configuration from disk."""
        runner_instance = MagicMock()
        mock_runner.return_value = runner_instance
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "blueprint.json"
            config_data = {"build": {"step": {"module": "custom", "args": {}}}}

            config_path.write_text(json.dumps(config_data), encoding="utf-8")
            mock_json_load.return_value = config_data

            original_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)
                custom_module = MagicMock()
                engine = ExecutionEngine({"custom": custom_module})
                engine.run("build")
            finally:
                os.chdir(original_cwd)

        mock_json_load.assert_called_once()
        custom_module.run.assert_called_once_with(runner_instance, {})
