# -*- coding: utf-8 -*-
from .compmake_test import CompmakeTest
from nose.tools import istest


def job_success(*args, **kwargs):
    pass


def job_failure(*args, **kwargs):  # @UnusedVariable
    assert False, 'asserting false'
  
  
@istest
class TestAssertion(CompmakeTest):

    def mySetUp(self):
        pass

    def testAssertion1(self):
        for i in range(10):
            self.comp(job_failure, job_id='fail%d' % i)
        
        def run():
            self.cc.batch_command('parmake n=2')
        self.assertMakeFailed(run, nfailed=10, nblocked=0)
