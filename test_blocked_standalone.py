#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Standalone version of test_blocked to test pytest conversion.
"""

import os
import sys
import pytest
from tempfile import mkdtemp
from shutil import rmtree

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from compmake import set_compmake_config, logger
from compmake.context import Context
from compmake.exceptions import CommandFailed, MakeFailed
from compmake.jobs import get_job, parse_job_list, get_job_cache
from compmake.scripts.master import compmake_main
from compmake.storage import StorageFilesystem
from compmake.structures import Job, Cache
from contracts import contract

# Helper functions from original test
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

# Test base class
class CompmakeTestBase:
    """Base class for pytest-based compmake tests."""
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Setup and teardown for each test."""
        self.root0 = mkdtemp()
        self.root = os.path.join(self.root0, 'compmake')
        self.db = StorageFilesystem(self.root, compress=True)
        self.cc = Context(db=self.db)
        # don't use '\r'
        set_compmake_config('interactive', False)
        set_compmake_config('console_status', False)

        from compmake.constants import CompmakeConstants
        CompmakeConstants.debug_check_invariants = True
        
        # Call the user-defined setup if it exists
        if hasattr(self, "mySetUp"):
            self.mySetUp()
        
        yield  # This is where the test will run
        
        # Teardown logic
        if True:
            print('not deleting %s' % self.root0)
        else:
            rmtree(self.root0)
        from multiprocessing import active_children
        c = active_children()
        print('active children: %s' % c)
        if c:
            if True:
                msg = 'Still active children: %s' % c
                logger.warning(msg)
            else:
                raise Exception(msg)

    # Helper methods
    def comp(self, *args, **kwargs):
        return self.cc.comp(*args, **kwargs)

    def assertMakeFailed(self, func, nfailed, nblocked):
        try:
            func()
            pytest.fail("Expected MakeFailed but no exception was raised")
        except MakeFailed as e:
            if len(e.failed) != nfailed:
                msg = 'Expected %d failed, got %d: %s' % (
                    nfailed, len(e.failed), e.failed)
                pytest.fail(msg)
            if len(e.blocked) != nblocked:
                msg = 'Expected %d blocked, got %d: %s' % (
                    nblocked, len(e.blocked), e.blocked)
                pytest.fail(msg)
        except Exception as e:
            pytest.fail('unexpected: %s' % e)

# Actual test
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
    # Run the tests directly
    exit_code = pytest.main(["-xvs", __file__])
    sys.exit(exit_code)