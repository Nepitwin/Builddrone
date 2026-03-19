from Builddrone.BaseModule import BaseModule


class CompressModule(BaseModule):
    def run(self, args):
        print("Compress module executed")
        print(args)