# -*- coding: utf-8 -*-
import pytest
from .pytest_base import CompmakeTestBase


def job_success(*args, **kwargs):
    pass


def job_failure(*args, **kwargs):  # @UnusedVariable
    assert False, 'asserting false'
  
  
class TestAssertion(CompmakeTestBase):

    def mySetUp(self):
        pass

    def test_assertion_1(self):
        for i in range(10):
            self.comp(job_failure, job_id='fail%d' % i)
        
        def run():
            # Use regular 'make' instead of 'parmake' to avoid multiprocessing issues
            self.cc.batch_command('make')
        self.assertMakeFailed(run, nfailed=10, nblocked=0)