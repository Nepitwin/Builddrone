import json


class ExecutionEngine:
    def __init__(self, modules: dict):
        self.modules = modules

    def run(self, config_path: str, stage: str):
        config = self._load_config(config_path)

        if stage not in config:
            raise Exception(f"Stage '{stage}' not found in config")

        print(f"\n== Stage: {stage} ==")

        steps = config[stage]

        for step_name, step in steps.items():
            self._execute_step(step_name, step)

    def _execute_step(self, step_name: str, step: dict):
        module_name = step.get("module")
        args = step.get("args", {})

        print(f"Running step: {step_name} ({module_name})")

        module = self.modules.get(module_name)

        if not module:
            raise Exception(f"Unknown module: {module_name}")

        module.run(args)

    @staticmethod
    def _load_config(path: str):
        with open(path) as f:
            return json.load(f)
