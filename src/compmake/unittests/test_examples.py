from contextlib import contextmanager
from system_cmd import system_cmd_result
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


def run_example(name):
    examples = get_examples_path()
    pyfile = os.path.join(examples, '%s.py' % name)
    if not os.path.exists(pyfile):
        msg = 'Example file does not exist: %s' % pyfile
        raise Exception(msg)

    with create_tmp_dir() as cwd:
        cmd = [pyfile, 'make recurse=1']
        system_cmd_result(cwd, cmd, 
                          display_stdout=True,
                          display_stderr=True,
                          raise_on_error=True)
    

@contextmanager
def create_tmp_dir():
    dirname = tempfile.mkdtemp()
    try:
        yield dirname
    except:
        raise


def test_example_big():
    run_example('example_big')

def test_example_dynamic_explicitcontext():
    run_example('example_dynamic_explicitcontext')

def test_example_progress():
    run_example('example_progress')

def test_example_progress_same():
    run_example('example_progress_same')

def test_example_simple():
    run_example('example_simple')


