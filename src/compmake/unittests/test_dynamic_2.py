# -*- coding: utf-8 -*-
import pytest
from .pytest_base import CompmakeTestBase
from compmake.unittests.mockup import mockup_recursive_5


class TestDynamic2(CompmakeTestBase):

    def test_dynamic2(self):
        mockup_recursive_5(self.cc)
        for _ in range(5):
            self.assert_cmd_success('ls;make;ls')
        self.assertJobsEqual('all', ['r1', 'r2', 'r3', 'r4', 'r5'])
        self.assertJobsEqual('done', ['r1', 'r2', 'r3', 'r4', 'r5'])

        self.assert_cmd_success('details r5')
        self.assert_cmd_success('details r4')
        self.assert_cmd_success('details r3')
        self.assert_cmd_success('details r2')
        self.assert_cmd_success('details r1')

        self.assert_defined_by('r5', ['root'])
        self.assert_defined_by('r4', ['root', 'r5'])
        self.assert_defined_by('r3', ['root', 'r5', 'r4'])
        self.assert_defined_by('r2', ['root', 'r5', 'r4', 'r3'])
        self.assert_defined_by('r1', ['root', 'r5', 'r4', 'r3', 'r2'])