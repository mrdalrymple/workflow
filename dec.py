import workflow as wf

@wf.stage("lib")
def build_lib():
    print("build -- lib")

@wf.stage("lib_dyn")
#@stage
#@depends("hello")
@wf.depends("lib")
def lib_dyn():
    print("build -- lib_dyn")


@wf.stage("exe")
@wf.depends("lib")
#@wf.depends("lib_dyn")
#@wf.depends("build-lib")
@wf.depends(lib_dyn)
def build():
    print("build -- exe")

#####################

if __name__ == '__main__':
    wf.main()
