"""Robot Framework test module."""

from builddrone.module.robotframework.robotframework_base_module import (
    RobotframeworkBaseModule,
)


class RobotframeworkTestModule(  # pylint: disable=too-few-public-methods
    RobotframeworkBaseModule
):
    """A module responsible for running Robot Framework test suites.

    Blueprint configuration arguments:
        "arguments": "Dictionary of CLI arguments to pass to robot"
        "cwd": "Optional working directory to run robot from"
    """

    command_prefix = ["-m", "robot"]
    log_message = "Robot..."
    failure_label = "Robot"
