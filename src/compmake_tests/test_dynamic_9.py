from .utils import Env, run_with_env


def always():
    print("always()")
    pass


def other():
    print("other()")
    pass


def dep():
    res = TestDynamic9.define_other
    print("other() returns %s" % res)
    return res


def fd(context, dep):
    context.comp(always)
    print("fd() sees dep=%s" % dep)
    if dep:
        context.comp(other)


def mockup9(context):
    depres = context.comp(dep)
    context.comp_dynamic(fd, dep=depres)


class TestDynamic9:
    define_other = True


@run_with_env
async def test_dynamic9(env: Env):
    """Re-execution creates more jobs."""
    mockup9(env)
    await env.assert_cmd_success("config echo 1")
    await env.assert_cmd_success("config echo_stdout 1")
    await env.assert_cmd_success("config echo_stderr 1")
    # self.assert_cmd_success('config console_status 1')
    # run it

    TestDynamic9.define_other = True  # returned by dep
    await env.assert_cmd_success("make recurse=1")
    await env.assert_cmd_success("stats")
    # we have 4 jobs defined
    await env.assert_jobs_equal("all", ["fd", "fd-always", "fd-other", "dep"])
    # clean and remake fd
    TestDynamic9.define_other = False  # returned by dep
    # clean dep
    await env.assert_cmd_success("remake dep")
    await env.assert_cmd_success("stats")
    # now all jobs are done
    await env.assert_jobs_equal("done", ["fd", "fd-always", "fd-other", "dep"])
    # but fd is not up to date
    await env.assert_job_uptodate("fd", False)

    await env.assert_cmd_success("make echo=1")  # remaking
    # now the "other" job should disappear
    await env.assert_cmd_success("stats")
    await env.assert_jobs_equal("all", ["fd", "fd-always", "dep"])
