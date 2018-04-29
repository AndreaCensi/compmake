# -*- coding: utf-8 -*-
from nose.tools import istest

from .compmake_test import CompmakeTest
from .mockup import mockup_recursive_5


@istest
class TestDynamic2rec(CompmakeTest):

    def test_dynamic1(self):
        mockup_recursive_5(self.cc)
        self.assert_cmd_success('parmake recurse=1;ls')
        self.assertJobsEqual('all', ['r1', 'r2', 'r3', 'r4', 'r5'])
        self.assertJobsEqual('done', ['r1', 'r2', 'r3', 'r4', 'r5'])

