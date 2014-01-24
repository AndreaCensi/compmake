from nose.tools import istest

from compmake.unittests.compmake_test import CompmakeTest


def recursive(context, v):
    if v == 0:
        print('finally!')
        return

    context.comp_dynamic(recursive, v - 1, job_id='r%d' % v)

def f():
    pass

def g(context):
    context.comp(f, job_id='ciao') # wrong
    
    
@istest
class TestDynamic3(CompmakeTest):

    howmany = None  # used by cases()

    def test_dynamic1(self):
        context = self.cc
        context.comp(f, job_id='ciao')
        self.assert_cmd_success('make')
        context.comp_dynamic(g, job_id='g')
        self.assert_cmd_fail('make g')
