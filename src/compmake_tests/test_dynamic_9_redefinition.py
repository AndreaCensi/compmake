import unittest
from multiprocessing import active_children

from .utils import Env, run_with_env


def g(b1, b2):
    pass


def f(context, level):
    if level == 0:
        context.comp(g, 1, 1)
    else:
        context.comp_dynamic(f, level - 1)
        # if level >= 2 or random.random() < 0.5:
        context.comp_dynamic(f, level - 1)


def mockup(context):
    context.comp_dynamic(f, 5)


# if False:
#
#     def test_dynamic9_redefinition(self):
#         mockup(env)
#         self.assert_cmd_success("make recurse=1")
#
#         assert_equal(len(self.get_jobs("g()")), 32)
#         assert_equal(len(self.get_jobs("f()")), 63)
#
#         self.assert_cmd_success("clean")
#         self.assert_jobs_equal("all", ["f"])
#
#         self.assert_cmd_success("make recurse=1")
#
#         assert_equal(len(self.get_jobs("g()")), 32)
#         assert_equal(len(self.get_jobs("f()")), 63)


@run_with_env
async def test_dynamic9_red_rmake(env: Env) -> None:
    mockup(env)
    env.sti.logger.info("part 1")
    await env.assert_cmd_success("rmake")
    await env.assert_cmd_success("ls")
    # ac =  active_children()
    # print('active children: %s' % ac)
    # showtree()
    # for a in ac:
    #     Process
    env.sti.logger.info("part 2")
    # assert not active_children()
    env.assert_equal(len(await env.get_jobs("g()")), 32)
    env.assert_equal(len(await env.get_jobs("f()")), 63)

    await env.assert_cmd_success("clean")
    await env.assert_jobs_equal("all", ["f"])

    # await env.assert_cmd_success("parmake recurse=1")
    await env.assert_cmd_success("rmake")
    # assert not active_children()

    env.assert_equal(len(await env.get_jobs("g()")), 32)
    env.assert_equal(len(await env.get_jobs("f()")), 63)


@unittest.skip
@run_with_env
async def test_dynamic9_red_rparmake(env: Env) -> None:
    mockup(env)
    env.sti.logger.info("part 1")
    await env.assert_cmd_success("parmake recurse=1")
    await env.assert_cmd_success("ls")
    # ac =  active_children()
    # print('active children: %s' % ac)
    # showtree()
    # for a in ac:
    #     Process
    env.sti.logger.info("part 2")
    assert not active_children()
    env.assert_equal(len(await env.get_jobs("g()")), 32)
    env.assert_equal(len(await env.get_jobs("f()")), 63)

    await env.assert_cmd_success("clean")
    await env.assert_jobs_equal("all", ["f"])

    await env.assert_cmd_success("parmake recurse=1")
    assert not active_children()

    env.assert_equal(len(await env.get_jobs("g()")), 32)
    env.assert_equal(len(await env.get_jobs("f()")), 63)


# import os
# def showtree():
#     print('showing process tree')
#     parent = psutil.Process(os.getpid())
#     for child in parent.children(recursive=True):
#         print("child: %s"%child)
#         child.kill()

#     if including_parent:
#         parent.kill()
#
# ## get the pid of this program
# pid=os.getpid()
#
# ## when you want to kill everything, including this program
# killtree(pid)
