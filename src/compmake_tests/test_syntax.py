import sys

from nose.tools import assert_equal, assert_raises

from compmake import Cache, CompmakeSyntaxError, get_job_cache, parse_job_list, set_job_cache
from compmake.types import CMJobID
from .utils import Env, run_with_env


def dummy():  # pragma: no cover
    pass


@run_with_env
async def test_syntax(env: Env):
    jobs = [
        ("a", Cache.DONE),
        ("b", Cache.FAILED),
        ("c", Cache.NOT_STARTED),
        ("d", Cache.DONE),
        ("e", Cache.DONE),
        #             ('f', Cache.IN_PROGRESS),
        ("g", Cache.DONE),
        ("h", Cache.FAILED),
        ("i", Cache.DONE),
        ("ii", Cache.DONE),
        ("v_rangefinder_nonunif-plot_tensors_tex-0", Cache.DONE),
    ]

    for job_id, state in jobs:
        env.comp(dummy, job_id=job_id)
        cache = get_job_cache(CMJobID(job_id), db=env.db)
        cache.state = state
        set_job_cache(CMJobID(job_id), cache, db=env.db)

    all_jobs = set([job_id for job_id, state in jobs])
    selectf = lambda S: set([nid for nid, state_ in jobs if state_ == S])
    failed = selectf(Cache.FAILED)
    done = selectf(Cache.DONE)
    #         self.in_progress = selectf(Cache.IN_PROGRESS)
    not_started = selectf(Cache.NOT_STARTED)

    def selection(crit):
        return set([nid_ for nid_, state_ in jobs if crit(nid_, state_)])

    def expandsTo(A, B):
        """ A, B can be:
        - set or list: list of jobs
        - string: passed to expands_jobs
        - lambda: passed to selection()
        """

        def expand_to_set(X):
            if isinstance(X, set):
                return X
            elif isinstance(X, list):
                return set(X)
            elif isinstance(X, type(lambda: 0)):
                return selection(X)
            elif isinstance(X, str):
                return set(parse_job_list(X, context=env.cc))
            else:
                assert False, "Wrong type %s" % type(X)

        a = expand_to_set(A)
        b = expand_to_set(B)

        try:
            assert_equal(set(a), set(b))
        except:  # pragma: no cover
            sys.stdout.write("Comparing:\n\t- %s\n\t   -> %s \n\t- %s\n\t   -> %s. \n" % (A, a, B, b))
            raise

    def syntaxError(s: str):
        def f(x):  # it's a generator, you should try to read it
            return list(parse_job_list(x, context=env.cc))

        assert_raises(CompmakeSyntaxError, f, s)

    # def userError(self, s):
    #     assert_raises(UserError, parse_job_list, s)

    syntaxError("not")
    syntaxError("all not")
    syntaxError("all not")
    syntaxError("all in")
    syntaxError("in $all")
    syntaxError("all not e")

    # def testSpecial(self):
    """ Test that the special variables work"""
    expandsTo("  ", set())
    expandsTo("all", all_jobs)
    expandsTo("failed", failed)
    expandsTo("done", done)
    expandsTo("DONE", done)

    #         expandsTo('in_progress', self.in_progress)

    """ Testing basic union operator """
    expandsTo("failed e", failed.union("e"))
    expandsTo("e failed", failed.union("e"))

    all_not_e = selection(lambda job, _: job != "e")
    expandsTo("e", ["e"])
    expandsTo("e*", ["e"])
    expandsTo("not e", all_not_e)
    expandsTo("not e*", all_not_e)
    expandsTo("all except e", all_not_e)
    expandsTo("not not e", ["e"])
    expandsTo("not not all", "all")
    expandsTo("not all", [])
    expandsTo("not all except all", [])
    expandsTo("not e except not e", [])
    expandsTo("not a b c except not a b c", [])
    expandsTo("not c except a ", "not a c")
    expandsTo("a in c  ", [])
    expandsTo("a in all  ", "a")
    expandsTo("all in all  ", "all")

    expandsTo("all except failed", lambda _, s_: s_ != Cache.FAILED)
    expandsTo("not failed", lambda _, s_: s_ != Cache.FAILED)

    expandsTo("a b in a b c", ["a", "b"])
    expandsTo("a b c in d e", [])

    # expandsTo("not started", not_started)
