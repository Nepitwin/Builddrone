"""Base module definition for builddrone modules."""

from abc import ABC, abstractmethod

from builddrone.runner import Runner


class BaseModule(ABC):  # pylint: disable=too-few-public-methods
    """Base class for all builddrone modules."""

    @abstractmethod
    def run(self, runner: Runner, args: dict) -> None:
        """Execute the module.

        Args:
            runner: Runner instance used to execute commands.
            args: Module configuration arguments.
        """
        raise NotImplementedError
