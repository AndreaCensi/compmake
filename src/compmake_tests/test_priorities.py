from zuper_commons.test_utils import my_assert_equal as assert_equal


from compmake import CompmakeConstants, set_compmake_status
from .utils import Env, run_with_env


def bottom():
    TestOrder.order.append("bottom")


def bottom2():
    TestOrder.order.append("bottom2")


def top(x):
    TestOrder.order.append("top")


class TestOrder:
    order = []


@run_with_env
async def test_order(env: Env) -> None:
    TestOrder.order = []
    set_compmake_status(CompmakeConstants.compmake_status_embedded)
    # add two copies
    env.comp(top, env.comp(bottom))
    env.comp(top, env.comp(bottom))

    await env.batch_command("clean")
    await env.batch_command("make")

    assert_equal(["bottom", "top", "bottom", "top"], TestOrder.order)


@run_with_env
async def test_order2(env: Env) -> None:
    TestOrder.order = []
    # choose wisely here
    env.comp(top, env.comp(bottom))
    env.comp(top, env.comp(bottom))
    env.comp(bottom2)

    await env.batch_command("clean")
    await env.batch_command("make")

    assert_equal(["bottom2", "bottom", "top", "bottom", "top"], TestOrder.order)


@run_with_env
async def test_order3(env: Env) -> None:
    TestOrder.order = []
    # choose wisely here
    env.comp(top, env.comp(bottom2))
    env.comp(bottom)
    env.comp(top, env.comp(bottom2))

    await env.batch_command("clean")
    await env.batch_command("make")

    assert_equal(["bottom", "bottom2", "top", "bottom2", "top"], TestOrder.order)
