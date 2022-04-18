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
        pass
    pass

class Stage:
    def __init__(self, name, func):
        self.name = name
        self.func = func
        self.deps = []


    def proc(self):
        if hasattr(self, "__stage_deps__"):
            self.deps.extend(self.__stage_deps__)
        if self.func and hasattr(self.func, "__stage_deps__"):
            self.deps.extend(self.func.__stage_deps__)

    def get_deps(self):
        return self.deps

    def fail(self, message):
        file = inspect.getsourcefile(self.func)
        print(f"FAIL(file): {file}")
        lines, lineno = inspect.getsourcelines(self.func)
        print(f"FAIL(lines):{lineno}")

    def __call__(self):
        if self.func:
            self.func()

_STGS = []
_STAGES = {}


def _add_dep(func, name, caller):
    if not hasattr(func, "__stage_deps__"):
        func.__stage_deps__ = []

    func.__stage_deps__.append(Dependency(name, caller))

import functools

def stage(name):
    #@functools.wraps(name)
    def decorator(func):
        _STAGES[name] = func
        _STGS.append(Stage(name, func))
        return func
    return decorator

from inspect import getframeinfo, stack

def depends(name):
    caller = getframeinfo(stack()[1][0])
    #print(f"caller={caller}")
    #print(f"--depends({name})")
    #@functools.wraps(name)
    def decorator(func):
        caller_stage_func = getframeinfo(stack()[1][0])
        #print(f"--depends({name})--dec({func})")
        _add_dep(func, name, caller)
        return func
    return decorator

#######

def _get_stages():
    return _STAGES.keys()

def _get_deps(name):
    deps = []
    func = _STAGES[name]
    if hasattr(func, "__stage_deps__"):
        deps = func.__stage_deps__
    return deps

def _run_stage(name):
    _STAGES[name]()

#######

import sys

def _print_dep_tree(dep_tree):
    print(f"-------- DEPS --------")
    for stage in dep_tree:
        deps = dep_tree[stage]
        print(f"{stage} -> {deps}")
    print(f"-------- ---- --------")

# main logic for the workflow framework
def _print_deco_error(dec, message):
    file = inspect.getsourcefile(dec)
    lines, lineno = inspect.getsourcelines(dec)
    func_name = dec.__name__
    print(f'File "{file}", line {lineno}')
    #print(f"  {func_name}()")
    print(f" >  {lines[0].strip()}")
    print(f"Error: {message}")

def _print_deco_error2(caller, message):
    file = caller.filename
    lineno = caller.lineno
    print(f"func: {caller.function}")
    print(f"index: {caller.index}")
    #func_name = dec.__name__
    print(f'File "{file}", line {lineno}')
    #print(f"  {func_name}()")
    for x in caller.code_context:
        print(f"=={x}")
    #print(f" >  {lines[0].strip()}")
    print(f"Error: {message}")

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

def main():
    stages = _STGS
    stage_names = []

    for stage in stages:
        stage.proc()
        stage_names.append(stage.name)

    dep_tree = {}
    stage_dict = {}
    for stage in stages:
        deps = stage.get_deps()
        dep_names = [x.name for x in deps]
        dep_tree[stage.name] = dep_names
        stage_dict[stage.name] = stage

    #print(f"stages: {stages}")
    # Validate deps
    for name, stage in stage_dict.items():
        deps = stage.get_deps()
        for dep in deps:
            if dep.name not in stage_names:
                _print_stage_dependency_error(stage, dep, f"Stage '{stage.name}', no such dependency: {dep.name}")
                #_print_deco_error(stage.func, f"stage: {stage.name}")
                #_print_deco_error2(dep.caller, f"Stage '{name}', no such dependency: {dep.name}")
                sys.exit(1)
                #stage.fail(f"no such dep: {dep}")
                #raise Exception(f"For stage '{name}', no such dependency: {dep}")

    _print_dep_tree(dep_tree)

    sorted_stages = get_sorted_list(dep_tree)

    for stage in sorted_stages:
        #_run_stage(stage)
        stage_dict[stage]()

def main_a():
    stages = _get_stages()

    dep_tree = {}
    for stage in stages:
        deps = _get_deps(stage)
        dep_tree[stage] = deps

    _print_dep_tree(dep_tree)

    sorted_stages = get_sorted_list(dep_tree)

    for stage in sorted_stages:
        _run_stage(stage)


######################

@stage("lib")
def build_lib():
    print("build -- lib")

@stage("exe")
@depends("lib")
@depends("lib_dyn")
def build():
    print("build -- exe")

@stage("lib_dyn")
@depends("hello")
@depends("lib")
def build_lib():
    print("build -- lib_dyn")

#print(build_lib.__name__)
#print(build.__name__)

#####################

if __name__ == '__main__':
    main()
