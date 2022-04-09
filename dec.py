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


def _add_dep(func, dep):
    if not hasattr(func, "__stage_deps__"):
        func.__stage_deps__ = []

    func.__stage_deps__.append(dep)


def stage(name):
    def decorator(func):
        _STAGES[name] = func
        _STGS.append(Stage(name, func))
        return func
    return decorator

def depends(name):
    def decorator(func):
        _add_dep(func, name)
        return func
    return decorator

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
    print(f"> {lines[0].strip()}")
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
        dep_tree[stage.name] = deps
        stage_dict[stage.name] = stage

    #print(f"stages: {stages}")
    # Validate deps
    for name, stage in stage_dict.items():
        deps = stage.get_deps()
        for dep in deps:
            if dep not in stage_names:
                _print_deco_error(stage.func, f"Stage '{name}', no such dependency: {dep}")
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
@depends("lib")
@depends("hello")
def build_lib():
    print("build -- lib_dyn")

#####################

if __name__ == '__main__':
    main()
