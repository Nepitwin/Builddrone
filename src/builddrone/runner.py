import subprocess
import os
import sys
import logging

class Runner:

    def __init__(self):
        # Set up basic logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        self._python_path = sys.executable
        if not self._python_path:
            raise RuntimeError("Python executable not found")

    def set_runner(self, python_path):
        if os.path.exists(python_path) and os.path.isfile(python_path):
            print("Setting python")
            self._python_path = python_path

    def reset_runner(self):
        self._python_path = sys.executable
        if not self._python_path:
            raise RuntimeError("Python executable not found")

    def run(self, cmd, cwd=None) -> int:
        full_cmd = [self._python_path] + cmd
        print(f"\n>>> {' '.join(map(str, full_cmd))}")
        result = subprocess.run(full_cmd, cwd=cwd)
        return result.returncode
