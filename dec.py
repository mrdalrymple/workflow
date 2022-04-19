########################################

from collections import defaultdict

class Graph:
    def __init__(self, nodes):
        self._edges = defaultdict(list)
        self._nodes = nodes

    def edge(self, origin, target):
        self._edges[origin].append(target)

    def _topo_sort_util(self, origin_node, visited, stack):
        visited.append(origin_node)

        for target_node in self._edges[origin_node]:
            if target_node not in visited:
                self._topo_sort_util(target_node, visited, stack)

        stack.append(origin_node)

    def topological_sort(self):
        visited_nodes = []
        sorted_nodes = [] # this will be a stack

        for node in self._nodes:
            if node not in visited_nodes:
                self._topo_sort_util(node, visited_nodes, sorted_nodes)

        return sorted_nodes

def get_sorted_list(dep_tree):
    nodes = dep_tree.keys()

    graph = Graph(nodes)

    for node, deps in dep_tree.items():
        for dep in deps:
            graph.edge(node, dep)

    return graph.topological_sort()

########################################

import inspect

class Dependency:
    def __init__(self, name, caller):
        self.name = name
        self.caller = caller

class Stage:
    def __init__(self, name, func, deps=None):
        self.name = name
        self.func = func
        self.deps = []

        if deps:
            self.deps.extend(deps)


    def proc(self):
        if hasattr(self, "__stage_deps__"):
            self.deps.extend(self.__stage_deps__)
            del self.__stage_deps__
        if self.func and hasattr(self.func, "__stage_deps__"):
            self.deps.extend(self.func.__stage_deps__)
            del self.func.__stage_deps__

    def get_deps(self):
        return self.deps

    def __call__(self, *args, **kwargs):
        if self.func:
            self.func(*args, **kwargs)

class StageManager:
    def __init__(self):
        self.stages = []
    
    def add(self, stage):
        self.stages.append(stage)

    def get_names(self):
        return [x.name for x in self.stages]

    def proc_all(self):
        for stage in self.stages:
            stage.proc()


########################################

_STAGE_MANAGER = StageManager()


def _add_dep(func, dependency):
    if isinstance(func, Stage):
        func.deps.append(dependency)
    else:
        if not hasattr(func, "__stage_deps__"):
            func.__stage_deps__ = []

        func.__stage_deps__.append(dependency)

#import functools
from inspect import getframeinfo, stack

def stage(name):

    func = None
    if callable(name):
        func = name
        name = None


    #@functools.wraps(name)
    def decorator(f):
        deps = None
        if hasattr(f, "__stage_deps__"):
            deps = f.__stage_deps__
            del f.__stage_deps__

        s = Stage(
            name=name or f.__name__,
            func=f,
            deps=deps
        )

        _STAGE_MANAGER.add(s)
        s.__doc__ = f.__doc__
        return s

    if func is not None:
        return decorator(func)

    return decorator


def depends(stage):
    caller = getframeinfo(stack()[1][0])

    #@functools.wraps(name)
    def decorator(func):
        #caller_stage_func = getframeinfo(stack()[1][0])

        # Did user pass in a stage/func or a string representing the stage?
        stage_name = None
        if isinstance(stage, Stage):
            stage_name = stage.name
        else:
            stage_name = stage

        _add_dep(func, Dependency(stage_name, caller))

        return func
    return decorator

########################################

import sys

def _print_dep_tree(dep_tree):
    print(f"-------- DEPS --------")
    for stage in dep_tree:
        deps = dep_tree[stage]
        print(f"{stage} -> {deps}")
    print(f"-------- ---- --------")

def _print_stage_dependency_error(stage, dependency, message):
    stage_file = inspect.getsourcefile(stage.func)
    stage_lines, stage_lineno = inspect.getsourcelines(stage.func)
    stage_module = inspect.getmodule(stage.func)
    #stage_module_name = inspect.getmodulename(stage.func)

    #print(f'  File "{stage_file}", line {stage_lineno}, in {stage_module}')
    print(f'  File "{stage_file}", line {stage_lineno}')
    print(f"    {stage_lines[0].strip()}")
    #print(f'  File "{dependency.caller.filename}", line {dependency.caller.lineno}, in {dependency.caller.name}')
    print(f'  File "{dependency.caller.filename}", line {dependency.caller.lineno}')
    print(f"    {dependency.caller.code_context[dependency.caller.index].strip()}")
    print(f"Error: {message}")

####################

def main():
    stage_manager = _STAGE_MANAGER
    stage_names = stage_manager.get_names()

    stage_manager.proc_all()

    dep_tree = {}
    stage_dict = {}
    for stage in stage_manager.stages:
        deps = stage.get_deps()
        dep_names = [x.name for x in deps]
        dep_tree[stage.name] = dep_names
        stage_dict[stage.name] = stage

    # Validate deps
    for name, stage in stage_dict.items():
        deps = stage.get_deps()
        for dep in deps:
            if dep.name not in stage_names:
                _print_stage_dependency_error(stage, dep, f"Stage '{stage.name}', no such dependency: {dep.name}")
                sys.exit(1)

    _print_dep_tree(dep_tree)

    sorted_STAGE_MANAGER = get_sorted_list(dep_tree)

    for stage in sorted_STAGE_MANAGER:
        stage_dict[stage]()


########################################

@stage("lib")
def build_lib():
    print("build -- lib")

@stage("lib_dyn")
#@stage
#@depends("hello")
@depends("lib")
def lib_dyn():
    print("build -- lib_dyn")


@depends("lib")
@stage("exe")
#@depends("lib_dyn")
#@depends("build-lib")
@depends(lib_dyn)
def build():
    print("build -- exe")

#####################

if __name__ == '__main__':
    main()
