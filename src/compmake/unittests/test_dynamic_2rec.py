# -*- coding: utf-8 -*-
import pytest
from .pytest_base import CompmakeTestBase
from .mockup import mockup_recursive_5


class TestDynamic2rec(CompmakeTestBase):

    def test_dynamic1(self):
        mockup_recursive_5(self.cc)
        self.assert_cmd_success('make recurse=1;ls')
        self.assertJobsEqual('all', ['r1', 'r2', 'r3', 'r4', 'r5'])
        self.assertJobsEqual('done', ['r1', 'r2', 'r3', 'r4', 'r5'])