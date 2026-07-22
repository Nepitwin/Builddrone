"""Command line interface for Builddrone."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from builddrone.drone_exception import DroneException
from builddrone.execution_engine import ExecutionEngine


def build_parser() -> argparse.ArgumentParser:
    """Create the Builddrone CLI parser."""
    parser = argparse.ArgumentParser(prog="python -m builddrone")
    parser.add_argument("stage", help="Pipeline stage to execute")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the Builddrone CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        engine = ExecutionEngine({})
        engine.run(args.stage)
    except DroneException as exc:
        parser.exit(1, f"{parser.prog}: error: {exc}\n")

    return 0
