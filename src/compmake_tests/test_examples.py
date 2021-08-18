import os
import tempfile
from contextlib import contextmanager

from zuper_commons.cmds import ExitCode
from zuper_commons.fs import DirPath
from zuper_commons.types import ZException
from zuper_utils_asyncio import SyncTaskInterface
from zuper_zapp import zapp1_test, ZappTestEnv
from zuper_zapp_interfaces import get_pi


def get_examples_path() -> DirPath:
    # from pkg_resources import resource_filename

    # here = resource_filename("compmake", "__init__.py")
    # examples = os.path.join(here, "..", "examples")
    examples = os.path.abspath("./examples")
    if not os.path.exists(examples):  # pragma: no cover
        msg = "Example dir does not exist."
        raise ZException(msg, examples=examples)
    return examples


async def run_example(sti: SyncTaskInterface, name: str, command: str, expect_fail: bool = False):
    examples = get_examples_path()
    pyfile = os.path.join(examples, f"{name}.py")
    if not os.path.exists(pyfile):  # pragma: no cover
        msg = f"Example file does not exist: {pyfile}"
        raise ZException(msg)

    logger = sti.logger

    pi = await get_pi(sti)
    logger.info(name=name, pyfile=pyfile, command=command, expect_fail=expect_fail)

    with create_tmp_dir() as cwd:
        cmd = [pyfile, command]

        async with pi.run3(*cmd, cwd=cwd, echo_stdout=True, echo_stderr=True) as p:

            status = await p.wait()
            stderr = await p.stderr_read()
            stdout = await p.stdout_read()
        if expect_fail:  # pragma: no cover
            msg = f"Expected failure of {name} but everything OK."
            raise ZException(msg, cmd=cmd, stderr=stderr, stdout=stdout)
        else:
            if status != ExitCode.OK:
                msg = f"Example {name!r}: Command {command!r} failed unexpectedly."
                raise ZException(msg, cmd=cmd, status=status, stderr=stderr, stdout=stdout)


@contextmanager
def create_tmp_dir():
    # FIXME: does not delete dir
    dirname = tempfile.mkdtemp()
    try:
        yield dirname
    except:  # pragma: no cover
        raise


cmd_make1 = "make recurse=1"
cmd_make2 = "parmake recurse=1"
cmd_make3 = "make recurse=1 new_process=1"
cmd_make4 = "parmake recurse=1 new_process=1"


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


@zapp1_test()
async def test_example_dynamic_explicitcontext1(ze: ZappTestEnv):
    await run_example(ze.sti, "example_dynamic_explicitcontext", cmd_make1)


@zapp1_test()
async def test_example_dynamic_explicitcontext2(ze: ZappTestEnv):
    await run_example(ze.sti, "example_dynamic_explicitcontext", cmd_make2)


@zapp1_test()
async def test_example_progress1(ze: ZappTestEnv):
    await run_example(ze.sti, "example_progress", cmd_make1)


@zapp1_test()
async def test_example_progress2(ze: ZappTestEnv):
    await run_example(ze.sti, "example_progress", cmd_make2)


@zapp1_test()
async def test_example_progress_same1(ze: ZappTestEnv):
    await run_example(ze.sti, "example_progress_same", cmd_make1)


@zapp1_test()
async def test_example_progress_same2(ze: ZappTestEnv):
    await run_example(ze.sti, "example_progress_same", cmd_make2)


@zapp1_test()
async def test_example_progress_same3(ze: ZappTestEnv):
    await run_example(ze.sti, "example_progress_same", cmd_make3)


@zapp1_test()
async def test_example_progress_same4(ze: ZappTestEnv):
    await run_example(ze.sti, "example_progress_same", cmd_make4)


@zapp1_test()
async def test_example_simple1(ze: ZappTestEnv):
    await run_example(ze.sti, "example_simple", cmd_make1)


@zapp1_test()
async def test_example_simple2(ze: ZappTestEnv):
    await run_example(ze.sti, "example_simple", cmd_make2)


#
# def test_example_external_support1():
#     run_example(ze.sti, "example_external_support", cmd_make1)
#
#
# def test_example_external_support2():
#     run_example(ze.sti, "example_external_support", cmd_make2)
#
#
# def test_example_external_support3():
#     run_example(ze.sti, "example_external_support", cmd_make3)
#
#
# def test_example_external_support4():
#     run_example(ze.sti, "example_external_support", cmd_make4)


@zapp1_test()
async def test_example_dynamic_explicitcontext3(ze: ZappTestEnv):
    await run_example(ze.sti, "example_dynamic_explicitcontext", cmd_make3)


@zapp1_test()
async def test_example_dynamic_explicitcontext4(ze: ZappTestEnv):
    await run_example(ze.sti, "example_dynamic_explicitcontext", cmd_make4)


@zapp1_test()
async def test_example_progress3(ze: ZappTestEnv):
    await run_example(ze.sti, "example_progress", cmd_make3)


@zapp1_test()
async def test_example_progress4(ze: ZappTestEnv):
    await run_example(ze.sti, "example_progress", cmd_make4)


@zapp1_test()
async def test_example_simple3(ze: ZappTestEnv):
    await run_example(ze.sti, "example_simple", cmd_make3)


@zapp1_test()
async def test_example_simple4(ze: ZappTestEnv):
    await run_example(ze.sti, "example_simple", cmd_make4)
