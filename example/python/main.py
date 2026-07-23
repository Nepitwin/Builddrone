"""Example application used by the Python blueprint.

The blueprint creates ``.venv`` automatically, installs the requirements, and
then runs the configured linting steps against this file.
"""


def main() -> None:
    """Run the Python example application."""
    print("Hello from main.py")


if __name__ == "__main__":
    main()
