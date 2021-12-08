def f():
    pass


def g(context):
    context.comp(f, job_id="ciao")  # this will become ciao-0


from .utils import Env, run_with_env


@run_with_env
async def test_dynamic3(env: Env) -> None:
    context = env.cc
    context.comp(f, job_id="ciao")
    await env.assert_cmd_success("ls")
    await env.assert_cmd_success("make")
    context.comp_dynamic(g, job_id="g")
    await env.assert_cmd_success("make g")
