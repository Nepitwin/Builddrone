"""Tests for the Builddrone exception type."""

import unittest

from builddrone.drone_exception import DroneException


class TestDroneException(unittest.TestCase):
    """Verify DroneException semantics."""

    def test_drone_exception_is_an_exception(self):
        """DroneException should inherit from Exception."""
        self.assertTrue(issubclass(DroneException, Exception))

    def test_drone_exception_preserves_message(self):
        """DroneException should preserve the provided message."""
        error = DroneException("boom")

        self.assertEqual(str(error), "boom")

    def test_drone_exception_can_be_raised(self):
        """DroneException should be catchable when raised."""
        with self.assertRaises(DroneException):
            raise DroneException("boom")
