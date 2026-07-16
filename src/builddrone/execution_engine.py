import json

from builddrone.base_module import BaseModule
from builddrone.module.filesystem.cleanup_module import CleanupModule as FilesystemCleanupModule
from builddrone.runner import Runner


class ExecutionEngine:
    def __init__(self, modules: dict[str, BaseModule]):
        self._modules = modules
        self._load_python_modules()
        self._load_filesystem_modules()
        self._runner = Runner()

    def run(self, config_path: str, stage: str) -> None:
        config = self._load_config(config_path)

        if stage not in config:
            raise Exception(f"Stage '{stage}' not found in config")

        print(f"\n== Stage: {stage} ==")

        steps = config[stage]

        for step_name, step in steps.items():
            self._execute_step(step_name, step)

    def _execute_step(self, step_name: str, step: dict) -> None:
        module_name = step.get("module", None)

        if module_name is None or not isinstance(module_name, str):
            raise Exception(f"Unknown module name")

        args = step.get("args", {})

        print(f"Running step: {step_name} ({module_name})")

        module = self._modules.get(module_name, None)

        if not module:
            raise Exception(f"Unknown module: {module_name}")

        module.run(self._runner, args)

    def _load_filesystem_modules(self) -> None:
        self._modules["filesystem.cleanup"] = FilesystemCleanupModule()

    def _load_python_modules(self) -> None:
        self._modules["python.build"] = PythonBuildModule()
        self._modules["python.install"] = PythonInstallModule()
        self._modules["python.pylint"] = PythonPylintModule()
        self._modules["python.venv"] = PythonVirtualEnvModule()

    @staticmethod
    def _load_config(path: str) -> dict:
        with open(path) as f:
            return json.load(f)