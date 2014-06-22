from nose.tools import istest

from .compmake_test import CompmakeTest



def rec(context, n):
    if n == 0:
        return 0
    else:
        recursive = context.comp_dynamic(rec, n - 1, job_id='rec-%s' % n)
        return context.comp(add, n, recursive, job_id='add-%s' % n)

def add(a, b):
    return a + b

def f(x):
    if not x == 15:
        raise ValueError('Expected 5 + 4 + 3 + 2 + 1 + 0 = 15, not %s' % x)


@istest
class TestDelegation2(CompmakeTest):

    def test_delegation_2(self):
        context = self.cc

        res = context.comp_dynamic(rec, 5, job_id='rec-main')
        context.comp(f, res)

        self.assert_cmd_success('ls')

        self.assert_cmd_success('make')

        self.assert_cmd_success('check-consistency')
