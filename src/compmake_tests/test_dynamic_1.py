from compmake import Context

from .utils import Env, run_test_with_env


def cases():
    """ Note this uses TestDynamic1.howmany """
    howmany = TestDynamic1.howmany
    assert isinstance(howmany, int)
    print(f"returned {howmany} cases")
    return range(howmany)


def actual_tst(value):
    print("actual_tst(value)")
    return value * 2


def generate_tsts(context, values):
    res = []
    for i, v in enumerate(values):
        res.append(context.comp(actual_tst, v, job_id="actual%d" % i))
    return context.comp(finish, res)


def finish(values):
    return sum(values)


def mockup_dynamic1(context: Context):
    values = context.comp(cases, job_id="values")
    context.comp_dynamic(generate_tsts, values, job_id="generate")


class TestDynamic1:

    howmany = None  # used by cases()


@run_test_with_env
async def test_dynamic1_cleaning(env: Env):
    mockup_dynamic1(env.cc)
    # At this point we have generated only two jobs
    await env.assert_jobs_equal("all", ["generate", "values"])

    # now we make them
    TestDynamic1.howmany = 3
    await env.assert_cmd_success("ls")
    await env.assert_cmd_success("make")
    await env.assert_cmd_success("ls")

    # this will have created new jobs
    await env.assert_jobs_equal(
        "all", ["generate", "values", "actual0", "actual1", "actual2", "generate-finish"]
    )
    # ... still to do
    await env.assert_jobs_equal("todo", ["actual0", "actual1", "actual2", "generate-finish"])

    # we can make them
    await env.assert_cmd_success("make")
    await env.assert_cmd_success("ls")
    await env.assert_jobs_equal(
        "done", ["generate", "values", "actual0", "actual1", "actual2", "generate-finish"]
    )

    # Now let's suppose we re-run values and it generates different number of mcdp_lang_tests

    # Now let's increase it to 4
    TestDynamic1.howmany = 4

    await env.assert_cmd_success("clean values; make generate")
    await env.assert_cmd_success("ls reason=1")

    await env.assert_jobs_equal(
        "all", ["generate", "values", "actual0", "actual1", "actual2", "actual3", "generate-finish"]
    )
    # some are done
    await env.assert_jobs_equal(
        "done", ["generate", "values", "actual0", "actual1", "actual2", "generate-finish"]
    )
    # but finish is not updtodate
    await env.assert_jobs_equal("uptodate", ["generate", "values", "actual0", "actual1", "actual2"])
    # some others are not
    await env.assert_jobs_equal("todo", ["actual3"])

    # now 2 jobs
    TestDynamic1.howmany = 2
    await env.assert_cmd_success("clean values")
    await env.assert_cmd_success("ls")
    await env.assert_cmd_success("make generate")
    await env.assert_cmd_success("ls")

    # Now we should have on job less because actual2 and 3 was not re-defined
    await env.assert_jobs_equal("all", ["generate", "values", "actual0", "actual1", "generate-finish"])
    # they should be all done, by the way
    await env.assert_jobs_equal("done", ["generate", "values", "actual0", "actual1", "generate-finish"])
