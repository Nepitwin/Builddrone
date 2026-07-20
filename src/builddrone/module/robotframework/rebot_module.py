"""Robot Framework rebot module."""

from builddrone.module.robotframework.robotframework_base_module import (
    RobotframeworkBaseModule,
)


class RobotframeworkRebotModule(  # pylint: disable=too-few-public-methods
    RobotframeworkBaseModule
):
    """A module responsible for running Robot Framework's rebot command.

    Blueprint configuration arguments:
        "arguments": "Dictionary of CLI arguments to pass to rebot"
        "cwd": "Optional working directory to run rebot from"
    """

    command_prefix = ["-m", "robot.rebot"]
    log_message = "Rebot..."
    failure_label = "Rebot"
