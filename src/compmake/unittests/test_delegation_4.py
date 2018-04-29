# -*- coding: utf-8 -*-
from nose.tools import istest

from .compmake_test import CompmakeTest


def rec(context, n):
    if n == 0:
        return 0
    return context.comp(add, n,
                        context.comp_dynamic(rec, n - 1, job_id='rec-%d' % n))

def add(a, b):
    return a + b

def f(x):
    if not x == 15:
        raise ValueError('Expected 5 + 4 + 3 + 2 + 1 + 0 = 15, not %s' % x)


@istest
class TestDelegation4(CompmakeTest):
    """ Similar to TestDelegation2 and 3, but here the jobs are not named
        exclusively with job_id=... """

    def test_delegation_4(self):
        context = self.cc

        res = context.comp_dynamic(rec, 5, job_id='rec-main')
        context.comp(f, res)

        self.assert_cmd_success('ls')

        self.assert_cmd_success('make')

        self.assert_cmd_success('check-consistency')
