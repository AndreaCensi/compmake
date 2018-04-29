# -*- coding: utf-8 -*-
from ..structures import Cache
from ..jobs import get_job_cache
from nose.tools import istest
from .compmake_test import CompmakeTest


def job_success(*args, **kwargs):
    pass


def job_failure(*args, **kwargs):
    raise ValueError('This job fails')


def check_job_states(db, **expected):
    for job_id, expected_status in expected.items():
        status = get_job_cache(job_id, db=db).state
        if status != expected_status:
            msg = ('For job %r I expected status %s but got status %s.' % 
                   (job_id, expected_status, status))
            raise Exception(msg)
 


@istest
class TestBlocked(CompmakeTest):

    def mySetUp(self):
        pass

    def testAdding(self):
        comp = self.comp

        A = comp(job_success, job_id='A')
        B = comp(job_failure, A, job_id='B')
        comp(job_success, B, job_id='C')
        
        
        def run():
            self.cc.batch_command('make')
        self.assertMakeFailed(run, nfailed=1, nblocked=1)

        check_job_states(self.db, A=Cache.DONE, B=Cache.FAILED, C=Cache.BLOCKED)
        
        
        
