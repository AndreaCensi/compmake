from compmake.unittests.compmake_test import CompmakeTest
from nose.tools import istest
# from ..structures import Cache
# from ..jobs import get_job_cache


def job_success(*args, **kwargs):
    pass


def job_failure(*args, **kwargs):  # @UnusedVariable
    assert False

#
# @compmake_environment
# def test_order():
#     from compmake import comp, batch_command
#     # make A -> B(fail) -> C
#     for i in range(10):
#         comp(job_failure, job_id='F%d' % i)
#     batch_command('parmake n=2')



@istest
class TestAssertion(CompmakeTest):

    def mySetUp(self):
        pass

    def testOrder(self):
        for i in range(10):
            self.comp(job_failure, job_id='F%d' % i)
        self.cc.batch_command('parmake n=2')

