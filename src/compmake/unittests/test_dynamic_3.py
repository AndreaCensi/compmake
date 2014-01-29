import functools

import nose
from nose.tools import istest

from compmake.unittests.compmake_test import CompmakeTest


def expected_failure(test):
    @functools.wraps(test)
    def inner(*args, **kwargs):
        try:
            test(*args, **kwargs)
        except Exception:
            raise nose.SkipTest
        else:
            raise AssertionError('Failure expected')
    return inner

def f():
    pass

def g(context):
    context.comp(f, job_id='ciao') # wrong
    
    
@istest
class TestDynamic3(CompmakeTest):

    howmany = None  # used by cases()

    @expected_failure
    def test_dynamic1(self):
        context = self.cc
        context.comp(f, job_id='ciao')
        self.assert_cmd_success('make')
        context.comp_dynamic(g, job_id='g')
        self.assert_cmd_fail('make g')

