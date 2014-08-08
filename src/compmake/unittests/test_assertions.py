from .compmake_test import CompmakeTest
from nose.tools import istest


def job_success(*args, **kwargs):
    pass


def job_failure(*args, **kwargs):  # @UnusedVariable
    assert False
  
  
@istest
class TestAssertion(CompmakeTest):

    def mySetUp(self):
        pass

    def testOrder(self):
        for i in range(10):
            self.comp(job_failure, job_id='F%d' % i)
        
        def run():
            self.cc.batch_command('parmake n=2')
        self.assertMakeFailed(run, nfailed=10, nblocked=0)
