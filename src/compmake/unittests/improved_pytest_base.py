# -*- coding: utf-8 -*-
import os
import pytest
from shutil import rmtree
from tempfile import mkdtemp
import uuid

from compmake import set_compmake_config, logger
from compmake.context import Context
from compmake.exceptions import CommandFailed, MakeFailed
from compmake.jobs import get_job, parse_job_list
from compmake.scripts.master import compmake_main
from compmake.storage import StorageFilesystem
from compmake.structures import Job
from contracts import contract

class CompmakeTestBase:
    """Base class for pytest-based compmake tests with improved isolation."""
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self, tmp_path):
        """Setup and teardown for each test.
        
        Uses pytest's tmp_path fixture for creating a unique directory for each test.
        """
        # Generate a unique identifier for this test run
        self.test_id = uuid.uuid4().hex[:8]
        
        # Use pytest's tmp_path fixture instead of mkdtemp for better cleanup
        self.root0 = str(tmp_path)
        self.root = os.path.join(self.root0, f'compmake_{self.test_id}')
        
        # Create db and context with the unique directory
        self.db = StorageFilesystem(self.root, compress=True)
        self.cc = Context(db=self.db)
        
        # Configure compmake with test-appropriate settings
        original_configs = {}
        # Save original configurations to restore them later
        original_configs['interactive'] = set_compmake_config('interactive', False)
        original_configs['console_status'] = set_compmake_config('console_status', False)
        
        # Save debug state to restore it later
        from compmake.constants import CompmakeConstants
        original_debug_check = CompmakeConstants.debug_check_invariants
        CompmakeConstants.debug_check_invariants = True
        
        # Call the user-defined setup if it exists
        if hasattr(self, "mySetUp"):
            self.mySetUp()
        
        yield  # This is where the test will run
        
        # Teardown logic
        from multiprocessing import active_children
        # Terminate any active children
        for child in active_children():
            try:
                child.terminate()
            except:
                pass
        
        # Restore original configurations
        for key, value in original_configs.items():
            set_compmake_config(key, value)
        
        # Restore debug state
        CompmakeConstants.debug_check_invariants = original_debug_check
        
        # Delete the temporary directory
        try:
            rmtree(self.root, ignore_errors=True)
        except Exception as e:
            logger.warning(f'Could not delete {self.root}: {e}')

    # Helper methods that remain the same
    def comp(self, *args, **kwargs):
        return self.cc.comp(*args, **kwargs)

    @contract(job_id=str, returns=Job)
    def get_job(self, job_id):
        db = self.cc.get_compmake_db()
        return get_job(job_id=job_id, db=db)

    def get_jobs(self, expression):
        """Returns the list of jobs corresponding to the given expression."""
        return list(parse_job_list(expression, context=self.cc))

    def assert_cmd_success(self, cmds):
        """Executes the (list of) commands and checks it was successful."""
        print('@ %s' % cmds)
        try:
            self.cc.batch_command(cmds)
        except MakeFailed as e:
            print('Detected MakeFailed')
            print('Failed jobs: %s' % e.failed)
            for job_id in e.failed:
                self.cc.interpret_commands_wrap('details %s' % job_id)
            raise
        except CommandFailed:
            raise

        self.cc.interpret_commands_wrap('check_consistency raise_if_error=1')

    def assert_cmd_fail(self, cmds):
        """Executes the (list of) commands and checks it was supposed to fail."""
        print('@ %s     [supposed to fail]' % cmds)
        try:
            self.cc.batch_command(cmds)
        except CommandFailed:
            pass
        else:
            msg = 'Command %r did not fail.' % cmds
            raise Exception(msg)

    @contract(cmd_string=str)
    def assert_cmd_success_script(self, cmd_string):
        """This runs the "compmake_main" script which recreates the DB and
        context from disk."""
        ret = compmake_main([self.root, '--nosysexit', '-c', cmd_string])
        assert ret == 0

    # Assertion methods
    def assert_defined_by(self, job_id, expected):
        assert self.get_job(job_id).defined_by == expected

    def assertEqualSet(self, a, b):
        assert set(a) == set(b)

    @contract(expr=str)
    def assertJobsEqual(self, expr, jobs, ignore_dyn_reports=True):
        js = self.get_jobs(expr)
        if ignore_dyn_reports:
            js = [x for x in js if not 'dynreports' in x]
        try:
            self.assertEqualSet(js, jobs)
        except:
            print('expr %r -> %s' % (expr, js))
            print('differs from %s' % jobs)
            raise

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

    def assert_job_uptodate(self, job_id, status):
        res = self.up_to_date(job_id)
        assert res == status, 'Want %r uptodate? %s' % (job_id, status)

    @contract(returns=bool)
    def up_to_date(self, job_id):
        from compmake.jobs.uptodate import CacheQueryDB
        cq = CacheQueryDB(db=self.db)
        up, reason, timestamp = cq.up_to_date(job_id)
        print('up_to_date(%r): %s, %r, %s' %
              (job_id, up, reason, timestamp))
        return up