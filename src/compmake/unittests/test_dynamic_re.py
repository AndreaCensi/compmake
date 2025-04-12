# -*- coding: utf-8 -*-
import pytest
from .pytest_base import CompmakeTestBase
from .test_dynamic_1 import mockup_dynamic1, TestDynamic1

class TestDynamic1rec(CompmakeTestBase):
    howmany = None  # used by cases()

    def test_dynamic1(self):
        TestDynamic1.howmany = 3
        mockup_dynamic1(self.cc)
        # At this point we have generated only two jobs
        self.assertJobsEqual('all', ['generate', 'values'])

        # now we make them
        self.assert_cmd_success('make recurse=1')

        # this will have created new jobs
        self.assertJobsEqual('all', ['generate', 'values', 'actual0', 
                                    'actual1', 'actual2', 'generate-finish'])
        # ... still to do
        self.assertJobsEqual('done', ['generate', 'values', 'actual0', 
                                     'actual1', 'actual2', 'generate-finish'])