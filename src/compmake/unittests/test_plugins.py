# -*- coding: utf-8 -*-
import pytest
import os
from .improved_pytest_base import CompmakeTestBase
from .mockup import mockup2_nofail


class TestPlugins(CompmakeTestBase):
    """Tests for various compmake plugins with improved isolation."""

    def mySetUp(self):
        # Setup that runs before each test
        mockup2_nofail(self.cc)

    @pytest.fixture(autouse=True)
    def cleanup_after_tests(self, tmp_path):
        # Create a special directory for test dumps
        self.dump_dir = os.path.join(str(tmp_path), "dumps")
        os.makedirs(self.dump_dir, exist_ok=True)
        yield
        # Any cleanup needed

    def test_details(self):
        jobs = self.get_jobs('all')
        for job_id in jobs:
            self.assert_cmd_success('details %s' % job_id)
        
        # Test with first two jobs if available
        if len(jobs) >= 2:
            self.assert_cmd_success('details %s %s' % (jobs[0], jobs[1]))

    def test_list(self):
        jobs = self.get_jobs('all')
        self.assert_cmd_success('ls')
        
        if jobs:
            self.assert_cmd_success('ls %s' % jobs[0])

    # @pytest.mark.skip(reason="Test disabled in original code")
    # def test_credits(self):
    #     self.assert_cmd_success('credits')

    def test_check_consistency(self):
        self.assert_cmd_success('check-consistency')

    def test_dump(self):
        # Use a unique directory for dumps in this test
        dirname = self.dump_dir
        
        # Test on done jobs
        jobs = self.get_jobs('done')
        for job_id in jobs:
            self.assert_cmd_success('dump directory=%s %s' % (dirname, job_id))

        # Test on not done jobs
        jobs = self.get_jobs('not done')
        for job_id in jobs:
            self.assert_cmd_success('dump directory=%s %s' % (dirname, job_id))