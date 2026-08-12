"""Robot Framework test module."""

from builddrone.drone_exception import DroneException
from builddrone.module.robotframework.robotframework_base_module import (
    RobotframeworkBaseModule,
)
from builddrone.runner import Runner


class RobotframeworkTestModule(  # pylint: disable=too-few-public-methods
    RobotframeworkBaseModule
):
    """A module responsible for running Robot Framework test suites.

    Blueprint configuration arguments:
        "arguments": "List of strings or single-entry key/value objects to pass to robot"
        "cwd": "Optional working directory to run robot from"
        "continueOnFailure": "When true, log robot failures and continue the stage"
    """

    command_prefix = ["-m", "robot"]
    log_message = "Robot..."
    failure_label = "Robot"

    def run(self, runner: Runner, args: dict) -> None:
        """Run robot and optionally defer failures until the stage completes."""
        continue_on_failure = args.get("continueOnFailure", False)
        if not isinstance(continue_on_failure, bool):
            raise DroneException("Argument 'continueOnFailure' must be a boolean")

        runner.logger.info(self.log_message)
        exit_code = self._run_command(runner, args)

        if exit_code == 0:
            return

        message = f"{self.failure_label} failed with exit code {exit_code}"
        if continue_on_failure:
            runner.record_failure(message)
            return

        raise DroneException(message)
