"""Example setup script for the filesystem blueprint."""

import os

def main() -> None:
    """Create the example structure used by the CLI."""
    folders = ["binaries", "dist", "build", "obj", "example"]
    for folder in folders:
        if not os.path.exists(folder):
            os.mkdir(folder)

    files = ["my_file.json", "my_file.yaml"]
    for file_path in files:
        if not os.path.exists(file_path):
            with open(file_path, "w", encoding="utf-8") as file:
                file.write("Temporary file for example execution\n")


if __name__ == "__main__":
    main()
