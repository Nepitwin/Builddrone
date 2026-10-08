"""Robot Framework rebot module."""

from builddrone.module.robotframework.robotframework_base_module import (
    RobotframeworkBaseModule,
)


class RobotframeworkRebotModule(  # pylint: disable=too-few-public-methods
    RobotframeworkBaseModule
):
    """A module responsible for running Robot Framework's rebot command.

    Blueprint configuration arguments:
        "arguments": "List of strings or single-entry key/value objects to pass to rebot"
        "cwd": "Optional working directory to run rebot from"

    Exit codes 1-250 (failed tests) are deferred like robot. Tool errors such
    as a missing output file still stop the stage immediately.
    """

    command_prefix = ["-m", "robot.rebot"]
    log_message = "Rebot..."
    failure_label = "Rebot"
