# -*- coding: utf-8 -*-
from .expected_fail import expected_failure
from contextlib import contextmanager
from contracts import indent
from system_cmd import CmdException, system_cmd_result
import os
import tempfile

def get_examples_path():
    from pkg_resources import resource_filename  # @UnresolvedImport
    here = resource_filename("compmake", "unittests")
    examples = os.path.join(here, '..', 'examples')
    examples = os.path.abspath(examples)
    if not os.path.exists(examples):
        msg = 'Example dir does not exist: %s' % examples
        raise Exception(msg)
    return examples


def run_example(name, command, expect_fail=False):
    examples = get_examples_path()
    pyfile = os.path.join(examples, '%s.py' % name)
    if not os.path.exists(pyfile):
        msg = 'Example file does not exist: %s' % pyfile
        raise Exception(msg)

    with create_tmp_dir() as cwd:
        cmd = [pyfile, command]
        try:
            res = system_cmd_result(cwd, cmd, 
                              display_stdout=False,
                              display_stderr=False,
                              raise_on_error=True)
            if expect_fail:
                msg = 'Expected failure of %s but everything OK.' % name
                msg += '\n cwd = %s'  % cwd 
                msg += '\n' + indent(res.stderr, 'stderr| ')
                msg += '\n' + indent(res.stdout, 'stdout| ')
                raise Exception(msg)
            return res
        except CmdException as e:
            stderr = e.res.stderr
            stdout = e.res.stdout
            if not expect_fail:
                msg = ('Example %r: Command %r failed unexpectedly.' % 
                       (name, command))
                msg += '\n retcode: %r' % e.res.ret
                msg += '\n' + indent(stderr, 'stderr| ')
                msg += '\n' + indent(stdout, 'stdout| ')
                raise Exception(msg)
            
                 
@contextmanager
def create_tmp_dir():
    # FIXME: does not delete dir
    dirname = tempfile.mkdtemp()
    try:
        yield dirname
    except:
        raise



cmd_make1 = 'make recurse=1'
cmd_make2 = 'parmake recurse=1'
cmd_make3 = 'make recurse=1 new_process=1'
cmd_make4 = 'parmake recurse=1 new_process=1'

# This gets slow
# def test_example_big1():
#     run_example('example_big', cmd_make1, expect_fail=True)
#     
# def test_example_big2():
#     run_example('example_big', cmd_make2, expect_fail=True)
# def test_example_big3():
#     run_example('example_big', cmd_make3, expect_fail=True)
# 
# def test_example_big4():
#     run_example('example_big', cmd_make4, expect_fail=True)

def test_example_dynamic_explicitcontext1():
    run_example('example_dynamic_explicitcontext', cmd_make1)

def test_example_dynamic_explicitcontext2():
    run_example('example_dynamic_explicitcontext', cmd_make2)
    
def test_example_progress1():
    run_example('example_progress', cmd_make1)

def test_example_progress2():
    run_example('example_progress', cmd_make2)


def test_example_progress_same1():
    run_example('example_progress_same', cmd_make1)

def test_example_progress_same2():
    run_example('example_progress_same', cmd_make2)

def test_example_progress_same3():
    run_example('example_progress_same', cmd_make3)
    
def test_example_progress_same4():
    run_example('example_progress_same', cmd_make4)

def test_example_simple1():
    run_example('example_simple', cmd_make1)
    
def test_example_simple2():
    run_example('example_simple', cmd_make2)

def example_external_support1():
    run_example('example_external_support', cmd_make1)

def example_external_support2():
    run_example('example_external_support', cmd_make2)
    
def example_external_support3():
    run_example('example_external_support', cmd_make3)
    
def example_external_support4():
    run_example('example_external_support', cmd_make4)

    
if True:  
        
    # Fails for pickle reasons
#     @expected_failure
    def test_example_dynamic_explicitcontext3():
        run_example('example_dynamic_explicitcontext', cmd_make3)
     
#     @expected_failure
    def test_example_dynamic_explicitcontext4():
        run_example('example_dynamic_explicitcontext', cmd_make4)
    
#     @expected_failure
    def test_example_progress3():
        run_example('example_progress', cmd_make3)
        
#     @expected_failure
    def test_example_progress4():
        run_example('example_progress', cmd_make4)
        
#     @expected_failure
    def test_example_simple3():
        run_example('example_simple', cmd_make3)
        
#     @expected_failure
    def test_example_simple4():
        run_example('example_simple', cmd_make4)
