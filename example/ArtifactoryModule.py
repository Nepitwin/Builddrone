from Builddrone.BaseModule import BaseModule


class ArtifactoryModule(BaseModule):
    def run(self, args):
        print("Artifactory module executed")
        print(args)