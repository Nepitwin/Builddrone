from Builddrone.BaseModule import BaseModule


class CompileModule(BaseModule):
    def run(self, args):
        print("Compile module executed")
        print(args)