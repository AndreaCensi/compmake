from typing import Any

from compmake import CompmakeConstants, set_compmake_status
from zuper_commons.test_utils import my_assert_equal
from .utils import Env, run_with_env


def add(s: str, other: Any = None) -> None:
    TestOrder.order.append(s)


class TestOrder:
    order = []


@run_with_env
async def test_order(env: Env) -> None:
    TestOrder.order = []
    set_compmake_status(CompmakeConstants.compmake_status_embedded)
    # add two copies
    env.comp(add, "A", env.comp(add, "B"))
    env.comp(add, "C", env.comp(add, "D"))

    await env.batch_command("clean")
    await env.batch_command("make")

    my_assert_equal(["B", "D", "A", "C"], TestOrder.order)


@run_with_env
async def test_order2(env: Env) -> None:
    TestOrder.order = []
    # choose wisely here
    env.comp(add, "A", env.comp(add, "B"))
    env.comp(add, "C", env.comp(add, "D"))

    env.comp(add, "E")

    await env.batch_command("clean")
    await env.batch_command("make")

    my_assert_equal(["B", "D", "A", "E", "C"], TestOrder.order)


@run_with_env
async def test_order3(env: Env) -> None:
    TestOrder.order = []
    # choose wisely here
    env.comp(add, "A", env.comp(add, "B"))
    env.comp(add, "C", env.comp(add, "D"))
    env.comp(add, "E")
    #
    # env.comp(top, env.comp(bottom2))
    # env.comp(bottom)
    # env.comp(top, env.comp(bottom2))

    await env.batch_command("clean")
    await env.batch_command("make")

    my_assert_equal(["B", "D", "A", "E", "C"], TestOrder.order)
