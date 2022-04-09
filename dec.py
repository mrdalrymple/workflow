class Stage:
    def __init__(self):
        self.params = []

_STAGES = {}
_DEPS = {}


def _param_memo(func, param):
    #if isinstance(func, Stage):
    #    func.params.append(param)
    #else:
    if not isinstance(func, Stage):
        if not hasattr(func, "__stage_params__"):
            func.__stage_params__ = []  # type: ignore

        func.__stage_params__.append(param)  # type: ignore


def stage(name):
    def decorator(func):
        _STAGES[name] = func
        return func
    return decorator

def depends(name):
    def decorator(func):
        _param_memo(func, name)
        return func
    return decorator

def _get_stages():
    return _STAGES.keys()

def _run_stage(name):
    _STAGES[name]()


def main():
    stages = _get_stages()
    
    for stage in stages:
        _run_stage(stage)


######################

@stage("lib")
def build_lib():
    print("build -- lib")


@stage("exe")
@depends("lib")
def build():
    print("build -- exe")

#####################

if __name__ == '__main__':
    main()
