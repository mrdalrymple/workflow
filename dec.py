import workflow as wf

from pathlib import Path

@wf.stage("lib")
def build_lib():
    print("build -- lib")

@wf.stage("lib_dyn")
@wf.depends("lib")
def lib_dyn():
    print("build -- lib_dyn")

@wf.stage("exe")
@wf.depends("lib")
@wf.depends(lib_dyn)
@wf.artifact("bin")
def build():
    print("build -- exe")
    Path("bin").mkdir(exist_ok=True)
    Path("bin", "myexe.exe").touch()

    #print(wf.get("STAGE_LIB_BIN"))

#####################

if __name__ == '__main__':
    wf.main()
