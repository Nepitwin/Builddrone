from Builddrone.ExecutionEngine import ExecutionEngine
from Example.ArtifactoryModule import ArtifactoryModule
from Example.CodesignModule import CodesignModule
from Example.CompileModule import CompileModule
from Example.CompressModule import CompressModule
from Example.ZipModule import ZipModule


modules = {
    "compile": CompileModule(),
    "codesign": CodesignModule(),
    "compress": CompressModule(),
    "zip": ZipModule(),
    "artifactory": ArtifactoryModule()
}

engine = ExecutionEngine(modules)
engine.run("Build.json", "build")
engine.run("Build.json", "upload")
