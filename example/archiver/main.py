"""Example setup script for the archiver blueprint."""

from pathlib import Path


def main() -> None:
    """Create sample files used by the archive stages."""
    result_dir = Path("result")
    nested_dir = result_dir / "nested"
    nested_dir.mkdir(parents=True, exist_ok=True)

    (result_dir / "summary.txt").write_text("Build summary\n", encoding="utf-8")
    (nested_dir / "data.txt").write_text("Nested output\n", encoding="utf-8")


if __name__ == "__main__":
    main()
