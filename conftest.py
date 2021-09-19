import pytest
import sys
import os.path
import types
import functools as ft
import threading
import os
import os.path
if sys.version_info[0] >= 3:
    import importlib
else:
    import imp
import collections
import ctypes
import re

# list of function names which shall not be
# traced when compression keyword hardening

def pytest_configure(config):
    """
    make no_compression mark available from pytest.mark.
    if not yet activated enable profiling of dump methods and functions
    and set compression_level selected on commandline if explicitly
    specified.
    """
    global _test_compression

    config.addinivalue_line(
        "markers","run_recover: run test with recoverd part of ahds.core module when direct import fails"
    )

# local handle of no_compression mark
run_recover = pytest.mark.run_recover

_core_import_failed = False

def pytest_sessionstart(session):
    """
    pytest hook called at start of session.
    - collects all functions exported by hickle.lookup module (for now) and
      records inserts "<filename>::<function.__qualname__>" strings into
      _trace_functions list for any not listed in above non_core_loader_functions
    - collects all dump_functions listed in class_register tables of all
      hickle.loaders.load_*.py modules.
    """

    global _core_import_failed

    core_module = sys.modules.get('ahds.core',None)
    if isinstance(core_module,types.ModuleType):
        return None

    fallback_collect = dict()

    def collect_fallback(frame,event,arg):
        if frame.f_code.co_name != '<module>' or frame.f_locals.get('__name__','') != 'ahds.core':
            return 
        if event == 'return':
            if arg is not None:
                return
        elif event != 'c_exception':
            return
        #print(frame.f_code.co_name,frame.f_locals.get('__name__'),'--',frame.f_locals.get('__module__','<nomodule>'),'--',frame.f_code.co_filename,event,"(",arg,")",file=collector_file,flush=True)
            
        #print('##',frame.f_locals.get('ahds_readonly_descriptor',None),frame.f_locals.get('ahds_parent_descriptor',None),frame.f_locals.get('BlockMetaClass'),file=collector_file,flush=True)
        fallback_collect.update(frame.f_locals)
    # extract all loader function from hickle.lookup

    current_profiler = sys.getprofile()
    sys.setprofile(collect_fallback)
    if sys.version_info[0] < 3:
        return None
    try:
        core_module_spec = importlib.util.find_spec("ahds.core")
        core_module = importlib.util.module_from_spec(core_module_spec)
        core_module_spec.loader.exec_module(core_module)
    except Exception:
        sys.setprofile(current_profiler)
        if not fallback_collect:
            raise
        core_module_spec = fallback_collect['__spec__']
    else:
        sys.setprofile(current_profiler)
        return None
    _core_import_failed = True
    package_path = os.path.dirname(__file__)
    core_module_fallback_spec = importlib.util.spec_from_file_location(core_module_spec.name,os.path.join(package_path,"tests","ahds_core_fallback.py"))
    core_module_fallback_spec.cached = None
    core_module_fallback = importlib.util.module_from_spec(core_module_fallback_spec)
    if core_module_fallback is None:
        raise Exception("fuck")
    core_module_fallback_spec.loader.exec_module(core_module_fallback)
    core_module_fallback.__dict__.update({key:value for key,value in fallback_collect.items() if key not in {'__spec__','__cached__','__loader__'}})
    sys.modules["ahds.core"] = core_module_fallback
    return None

def pytest_collection_finish(session):
    """
    collect all test functions for which comression related keyword monitoring
    shall be disabled.
    """

    global _core_import_failed

    if not _core_import_failed:
        return None

    listed = set()
    listemodules = set()
    for item in session.items:
        test_node = item.getparent(pytest.Class)
        if test_node is not None:
            for marker in test_node.iter_markers(run_recover.name):
                break
            else:
                test_node.add_marker(pytest.mark.xfail(True,reason="ahds.core module ImportError",run=False,strict=True))
            continue
        test_node = item.get_parent(pytest.Function)
        if test_node is None:
            continue
        for marker in test_node.iter_markers(run_recover.name):
            break
        else:
            test_node.add_marker(pytest.mark.xfail(True,reason="ahds.core module ImportError",run=False,strict=True))
