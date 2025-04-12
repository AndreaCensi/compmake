# -*- coding: utf-8 -*-
import pytest
import sys
import os

# Add the src directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

# Use absolute imports instead of relative
from compmake.structures import Cache
from compmake.jobs import get_job_cache
from compmake.unittests.pytest_base import CompmakeTestBase

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

class TestBlocked(CompmakeTestBase):
    def mySetUp(self):
        pass

    def test_adding(self):
        comp = self.comp

        A = comp(job_success, job_id='A')
        B = comp(job_failure, A, job_id='B')
        comp(job_success, B, job_id='C')
        
        def run():
            self.cc.batch_command('make')
        self.assertMakeFailed(run, nfailed=1, nblocked=1)

        check_job_states(self.db, A=Cache.DONE, B=Cache.FAILED, C=Cache.BLOCKED)

if __name__ == "__main__":
    # Run this test file directly
    pytest.main(["-xvs", __file__])