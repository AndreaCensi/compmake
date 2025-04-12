# -*- coding: utf-8 -*-
import sys
import pytest
from .pytest_base import CompmakeTestBase
from ..jobs import get_job_cache, set_job_cache
from ..structures import Cache
from ..exceptions import UserError, CompmakeSyntaxError
from ..ui import parse_job_list


def dummy():
    pass


class TestSyntax(CompmakeTestBase):
    def mySetUp(self):
        # Removed when refactoring
        # remove_all_jobs()
        # reset_jobs_definition_set()

        self.jobs = [
            ('a', Cache.DONE),
            ('b', Cache.FAILED),
            ('c', Cache.NOT_STARTED),
            ('d', Cache.DONE),
            ('e', Cache.DONE),
#             ('f', Cache.IN_PROGRESS),
            ('g', Cache.DONE),
            ('h', Cache.FAILED),
            ('i', Cache.DONE),
            ('ii', Cache.DONE),
            ('v_rangefinder_nonunif-plot_tensors_tex-0', Cache.DONE),
        ]

        for job_id, state in self.jobs:
            self.comp(dummy, job_id=job_id)
            cache = get_job_cache(job_id, db=self.db)
            cache.state = state
            set_job_cache(job_id, cache, db=self.db)

        self.all = set([job_id for job_id, state in self.jobs])
        selectf = lambda S: set([nid
                                 for nid, state_ in self.jobs
                                 if state_ == S])
        self.failed = selectf(Cache.FAILED)
        self.done = selectf(Cache.DONE)
#         self.in_progress = selectf(Cache.IN_PROGRESS)
        self.not_started = selectf(Cache.NOT_STARTED)

    def selection(self, crit):
        return set([nid for nid, state in self.jobs if crit(nid, state)])

    def expandsTo(self, A, B):
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
                return self.selection(X)
            elif isinstance(X, str):
                return set(parse_job_list(X, context=self.cc))
            else:
                assert False, 'Wrong type %s' % type(X)

        a = expand_to_set(A)
        b = expand_to_set(B)

        try:
            self.assertEqualSet(a, b)
        except:
            sys.stdout.write(
                'Comparing:\n\t- %s\n\t   -> %s \n\t- %s\n\t   -> %s. \n' % (
                    A, a, B, b))
            raise

    def syntaxError(self, s):
        def f(x):  # it's a generator, you should try to read it
            return list(parse_job_list(x, context=self.cc))

        with pytest.raises(CompmakeSyntaxError):
            f(s)

    def userError(self, s):
        with pytest.raises(UserError):
            parse_job_list(s)

    def test_catch_errors(self):
        self.syntaxError('not')
        self.syntaxError('all not')
        self.syntaxError('all not')
        self.syntaxError('all in')
        self.syntaxError('in $all')
        self.syntaxError('all not e')

    def test_special(self):
        """ Test that the special variables work"""
        self.expandsTo('  ', set())
        self.expandsTo('all', self.all)
        self.expandsTo('failed', self.failed)
        self.expandsTo('done', self.done)
        self.expandsTo('DONE', self.done)
#         self.expandsTo('in_progress', self.in_progress)

    def test_basic_union(self):
        """ Testing basic union operator """
        self.expandsTo('failed e', self.failed.union(set(['e'])))
        self.expandsTo('e failed', self.failed.union(set(['e'])))

    def test_not(self):
        all_not_e = self.selection(lambda job, _: job != 'e')
        self.expandsTo('e', ['e'])
        self.expandsTo('e*', ['e'])
        self.expandsTo('not e', all_not_e)
        self.expandsTo('not e*', all_not_e)
        self.expandsTo('all except e', all_not_e)
        self.expandsTo('not not e', ['e'])
        self.expandsTo('not not all', 'all')
        self.expandsTo('not all', [])
        self.expandsTo('not all except all', [])
        self.expandsTo('not e except not e', [])
        self.expandsTo('not a b c except not a b c', [])
        self.expandsTo('not c except a ', 'not a c')
        self.expandsTo('a in c  ', [])
        self.expandsTo('a in all  ', 'a')
        self.expandsTo('all in all  ', 'all')

    def test_failed(self):
        self.expandsTo('all except failed',
                       lambda _, state: state != Cache.FAILED)
        self.expandsTo('not failed', lambda _, state: state != Cache.FAILED)

    def test_intersection(self):
        self.expandsTo('a b in a b c', ['a', 'b'])
        self.expandsTo('a b c in d e', [])