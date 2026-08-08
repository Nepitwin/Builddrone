"""Example setup script for the archiver blueprint."""

import os


def main() -> None:
    """Create sample files used by the archive stages."""
    result_dir = "result"
    nested_dir = os.path.join(result_dir, "nested")
    os.makedirs(nested_dir, exist_ok=True)

    files = {
        os.path.join(result_dir, "summary.txt"): "Build summary\n",
        os.path.join(nested_dir, "data.txt"): "Nested output\n",
    }
    for file_path, content in files.items():
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(content)


if __name__ == "__main__":
    main()
