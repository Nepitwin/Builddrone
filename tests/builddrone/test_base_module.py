"""Tests for the Builddrone base module."""

import inspect
import unittest

from builddrone.base_module import BaseModule


class CompleteModule(BaseModule):  # pylint: disable=too-few-public-methods
    """Concrete module used to verify instantiation."""

    def run(self, _runner, _args):
        """Implement the abstract contract."""
        return None


class TestBaseModule(unittest.TestCase):
    """Verify the abstract base module contract."""

    def test_base_module_is_abstract(self):
        """BaseModule cannot be instantiated directly."""
        self.assertTrue(inspect.isabstract(BaseModule))

    def test_incomplete_subclass_is_abstract(self):
        """Subclasses that omit run remain abstract."""

        incomplete_module = type("IncompleteModule", (BaseModule,), {})

        self.assertTrue(inspect.isabstract(incomplete_module))

    def test_complete_subclass_can_be_instantiated(self):
        """Subclasses implementing run can be instantiated."""

        module = CompleteModule()

        self.assertIsInstance(module, BaseModule)
