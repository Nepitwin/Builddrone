"""Command line interface for Builddrone."""

from __future__ import annotations

import argparse
import logging
from collections.abc import Sequence

from builddrone.drone_exception import DroneException
from builddrone.execution_engine import ExecutionEngine
from builddrone.runner import configure_logging


def build_parser() -> argparse.ArgumentParser:
    """Create the Builddrone CLI parser."""
    parser = argparse.ArgumentParser(prog="python -m builddrone")
    parser.add_argument("stage", help="Pipeline stage to execute")
    return parser


def _log_drone_exception(prog: str, exc: DroneException) -> None:
    """Log a DroneException with its cause chain for CI diagnostics."""
    logger = logging.getLogger("builddrone.runner")
    logger.error("%s: error: %s", prog, exc)

    cause = exc.__cause__
    while cause is not None:
        logger.error("Caused by: %s: %s", type(cause).__name__, cause)
        cause = cause.__cause__


def main(argv: Sequence[str] | None = None) -> int:
    """Run the Builddrone CLI."""
    configure_logging()
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        engine = ExecutionEngine({})
        engine.run(args.stage)
    except DroneException as exc:
        _log_drone_exception(parser.prog, exc)
        return 1

    return 0
