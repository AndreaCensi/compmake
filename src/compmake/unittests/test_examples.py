from contextlib import contextmanager
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


def run_example(name, expect_fail=False):
    examples = get_examples_path()
    pyfile = os.path.join(examples, '%s.py' % name)
    if not os.path.exists(pyfile):
        msg = 'Example file does not exist: %s' % pyfile
        raise Exception(msg)

    with create_tmp_dir() as cwd:
        cmd = [pyfile, 'make recurse=1']
        try:
            system_cmd_result(cwd, cmd, 
                              display_stdout=False,
                              display_stderr=False,
                              raise_on_error=True)
            if expect_fail:
                raise Exception('Expected failure of %s' % name)
        except CmdException:
            if not expect_fail:
                raise
        
        

@contextmanager
def create_tmp_dir():
    # FIXME: does not delete dir
    dirname = tempfile.mkdtemp()
    try:
        yield dirname
    except:
        raise


def test_example_big():
    run_example('example_big', expect_fail=True)

def test_example_dynamic_explicitcontext():
    run_example('example_dynamic_explicitcontext')

def test_example_progress():
    run_example('example_progress')

def test_example_progress_same():
    run_example('example_progress_same')

def test_example_simple():
    run_example('example_simple')


