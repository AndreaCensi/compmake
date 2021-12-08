from .mockup import mockup2_fails, mockup2_nofail, mockup3
from .utils import Env, run_with_env


@run_with_env
async def test_plugin_details(env: Env) -> None:
    await mockup2_nofail(env)
    jobs = await env.get_jobs("all")
    for job_id in jobs:
        await env.assert_cmd_success("details %s" % job_id)
    await env.assert_cmd_success("details %s %s" % (jobs[0], jobs[1]))


@run_with_env
async def test_plugin_list(env: Env) -> None:
    await mockup2_nofail(env)
    jobs = await env.get_jobs("all")
    await env.assert_cmd_success("ls")
    await env.assert_cmd_success("ls %s" % jobs[0])


@run_with_env
async def test_plugin_check_consistency(env: Env) -> None:
    await mockup2_nofail(env)
    await env.assert_cmd_success("check-consistency")


@run_with_env
async def test_plugin_graph(env: Env) -> None:
    await mockup2_nofail(env)
    await env.assert_cmd_success("graph")


@run_with_env
async def test_plugin_commands_html(env: Env) -> None:
    await env.assert_cmd_success("commands_html")


@run_with_env
async def test_plugin_why(env: Env) -> None:
    await mockup2_fails(env)
    await env.assert_cmd_success("why fail1")


@run_with_env
async def test_plugin_gantt(env: Env) -> None:
    await mockup3(env)
    await env.assert_cmd_success("gantt")


@run_with_env
async def test_dump(env: Env) -> None:
    await mockup2_nofail(env)
    dirname = env.db.basepath
    jobs = await env.get_jobs("done")
    for job_id in jobs:
        await env.assert_cmd_success("dump directory=%s %s" % (dirname, job_id))

    # TODO: add check that it fails for not done
    jobs = await env.get_jobs("not done")
    for job_id in jobs:
        await env.assert_cmd_success("dump directory=%s %s" % (dirname, job_id))
