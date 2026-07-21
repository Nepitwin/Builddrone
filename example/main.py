"""Example entry point for running the cleanup stage."""

import os

from builddrone.execution_engine import ExecutionEngine


def main() -> None:
    """Create the example structure and run cleanup."""
    folders = ["binaries", "dist", "build", "obj", "example"]
    for folder in folders:
        if not os.path.exists(folder):
            os.mkdir(folder)

    files = ["example/blueprint.json", "example/blueprint.yaml"]
    for file_path in files:
        if not os.path.exists(file_path):
            with open(file_path, "w", encoding="utf-8") as file:
                file.write("Temporary file for example execution\n")

    modules = {}
    engine = ExecutionEngine(modules)

    engine.run("blueprint.json", "copy")
    engine.run("blueprint.json", "cleanup")


if __name__ == "__main__":
    main()
