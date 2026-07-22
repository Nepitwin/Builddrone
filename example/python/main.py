"""Create the virtual environment used by the Python example blueprint."""

import venv
from pathlib import Path

VIRTUAL_ENV = Path(".venv")


def main() -> None:
    """Create a local virtual environment with pip installed."""
    if VIRTUAL_ENV.is_dir():
        return

    venv.EnvBuilder(with_pip=True).create(VIRTUAL_ENV)


if __name__ == "__main__":
    main()
