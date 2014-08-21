from nose.tools import istest

from .compmake_test import CompmakeTest
from compmake.unittests.expected_fail import expected_failure

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

