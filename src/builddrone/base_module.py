from builddrone.runner import Runner


class BaseModule:
    def run(self, runner: Runner, args: dict) -> None:
        raise NotImplementedError()