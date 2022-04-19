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

class Artifact:
    def __init__(self, directory, caller=None):
        self.directory = directory
        self.caller = caller

class Dependency:
    def __init__(self, name, caller=None):
        self.name = name
        self.caller = caller

class Stage:
    def __init__(self, name, func, arts=None, deps=None):
        self.name = name
        self.func = func
        self.deps = []
        self.artifacts = []

        if deps:
            self.deps.extend(deps)

        if arts:
            self.artifacts.extend(arts)

    def get_deps(self):
        return self.deps

    def get_artifacts(self):
        return self.artifacts

    def __call__(self, *args, **kwargs):
        if self.func:
            self.func(*args, **kwargs)

####################

class StageManager:
    def __init__(self):
        self.stages = []
    
    def add(self, stage):
        self.stages.append(stage)

    def get_names(self):
        return [x.name for x in self.stages]


########################################

def get(env_variable):
    return os.environ[env_variable]

########################################

_STAGE_MANAGER = StageManager()


def _add_dep(func, dependency):
    if isinstance(func, Stage):
        func.deps.append(dependency)
    else:
        if not hasattr(func, "__stage_deps__"):
            func.__stage_deps__ = []

        func.__stage_deps__.append(dependency)

def _add_artifact(func, artifact):
    if isinstance(func, Stage):
        func.artifacts.append(artifact)
    else:
        if not hasattr(func, "__stage_arts__"):
            func.__stage_arts__ = []

        func.__stage_arts__.append(artifact)

from inspect import getframeinfo, stack

def stage(name):

    func = None
    if callable(name):
        func = name
        name = None

    def decorator(f):
        deps = None
        if hasattr(f, "__stage_deps__"):
            deps = f.__stage_deps__
            del f.__stage_deps__

        artifacts = None
        if hasattr(f, "__stage_arts__"):
            artifacts = f.__stage_arts__
            del f.__stage_arts__

        s = Stage(
            name=name or f.__name__,
            func=f,
            deps=deps,
            arts=artifacts
        )

        _STAGE_MANAGER.add(s)
        s.__doc__ = f.__doc__
        return s

    if func is not None:
        return decorator(func)

    return decorator


def depends(stage):
    caller = getframeinfo(stack()[1][0])

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

def artifact(directory):
    caller = getframeinfo(stack()[1][0])

    def decorator(func):
        _add_artifact(func, Artifact(directory, caller))
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

def _print_stage_dependency_error(message, stage, dependency=None):
    stage_file = inspect.getsourcefile(stage.func)
    stage_lines, stage_lineno = inspect.getsourcelines(stage.func)
    stage_module = inspect.getmodule(stage.func)
    #stage_module_name = inspect.getmodulename(stage.func)

    #print(f'  File "{stage_file}", line {stage_lineno}, in {stage_module}')
    print(f'  File "{stage_file}", line {stage_lineno}')
    print(f"    {stage_lines[0].strip()}")
    #print(f'  File "{dependency.caller.filename}", line {dependency.caller.lineno}, in {dependency.caller.name}')
    if dependency and dependency.caller:
        print(f'  File "{dependency.caller.filename}", line {dependency.caller.lineno}')
        print(f"    {dependency.caller.code_context[dependency.caller.index].strip()}")
    print(f"Error: {message}")

def _print_stage_artifact_error(message, stage):
    stage_file = inspect.getsourcefile(stage.func)
    stage_lines, stage_lineno = inspect.getsourcelines(stage.func)

    print(f'  File "{stage_file}", line {stage_lineno}')
    print(f"    {stage_lines[0].strip()}")

    print(f"Error: {message}")


####################

from pathlib import Path
import shutil

# TODO: directory param should instead be a storage driver (so it could be local or something else)
# Or should also take a storage driver, copy locally first, then upload to storage driver
def _save_artifact(stage, directory):
    wf_root = Path(".wf")
    artifact_root = Path(wf_root, "artifacts")
    stage_root = Path(artifact_root, stage.name)

    wf_root.mkdir(exist_ok=True)
    artifact_root.mkdir(exist_ok=True)

    # Cleanup existing directory (local build?)
    if stage_root.exists():
        shutil.rmtree(stage_root)

    shutil.copytree(directory, stage_root)

ENV_DEP_ART_PATH_PREFIX = "STAGE_"
ENV_DEP_ART_PATH_SUFFIX = "_BIN"

def _get_env_from_deps(stage, deps, prefix=None, suffix=None):
    wf_root = Path(".wf")
    artifact_root = Path(wf_root, "artifacts")

    if prefix is None:
        prefix = ENV_DEP_ART_PATH_PREFIX
    if suffix is None:
        suffix = ENV_DEP_ART_PATH_SUFFIX

    env = {}
    for dep in deps:
        env_name = f"{prefix}{dep.name}{suffix}".upper()
        env_value = str(Path(artifact_root, dep.name))
        env[env_name] = env_value

    return env

####################

import click
import os

@click.command()
@click.option("--stage", "target_stage")
@click.option("--show-dep-tree", is_flag=True)
def main(target_stage, show_dep_tree):
    stage_manager = _STAGE_MANAGER
    stage_names = stage_manager.get_names()

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
                _print_stage_dependency_error(f"Stage '{stage.name}', no such dependency: {dep.name}", stage, dep)
                sys.exit(1)

    # Validate artifacts (only 1 allowed)
    for _, stage in stage_dict.items():
        artifacts = stage.get_artifacts()
        art_count = len(artifacts)
        if art_count > 1:
            _print_stage_artifact_error(f"Stage '{stage.name}', only one artifact allowed, found: {art_count}", stage)
            sys.exit(1)

    if show_dep_tree:
        _print_dep_tree(dep_tree)

    # Determine stages to run
    if target_stage is not None:
        if target_stage not in stage_dict.keys():
            raise click.BadOptionUsage(target_stage, "Unknown stage")
        stages_to_run = [target_stage]
    else:
        stages_to_run = get_sorted_list(dep_tree)

    # Run stages
    for stage_name in stages_to_run:
        stage = stage_dict[stage_name]

        # Pull in dependencies and calculate their env variable name (that contains the path to get at the files)
        deps = stage.get_deps()
        stage_env = _get_env_from_deps(stage, deps)

        for key,value in stage_env.items():
            #print(f"{key}={value}")
            os.environ[key] = value

        # Run current stage
        stage()

        # Save stage artifact
        for artifact in stage.artifacts:
            dir = artifact.directory
            _save_artifact(stage, dir)



########################################
