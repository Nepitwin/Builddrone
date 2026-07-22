"""Tests for the Builddrone command line interface."""

import unittest
from unittest.mock import MagicMock, patch

from builddrone.cli import build_parser, main
from builddrone.drone_exception import DroneException


class TestBuilddroneCli(unittest.TestCase):
    """Verify CLI parsing and dispatch."""

    def test_build_parser_requires_stage(self):
        """The parser should require a stage argument."""
        parser = build_parser()

        with self.assertRaises(SystemExit) as context:
            parser.parse_args([])

        self.assertEqual(context.exception.code, 2)

    @patch("builddrone.cli.ExecutionEngine")
    def test_main_runs_requested_stage(self, mock_engine):
        """main should pass the requested stage to the execution engine."""
        engine_instance = MagicMock()
        mock_engine.return_value = engine_instance

        exit_code = main(["copy"])

        self.assertEqual(exit_code, 0)
        mock_engine.assert_called_once_with({})
        engine_instance.run.assert_called_once_with("copy")

    @patch("builddrone.cli.ExecutionEngine")
    def test_main_exits_with_error_on_drone_exception(self, mock_engine):
        """main should return a non-zero exit code when execution fails."""
        engine_instance = MagicMock()
        engine_instance.run.side_effect = DroneException("Stage 'copy' not found in config")
        mock_engine.return_value = engine_instance

        with self.assertRaises(SystemExit) as context:
            main(["copy"])

        self.assertEqual(context.exception.code, 1)
