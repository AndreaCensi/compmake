# -*- coding: utf-8 -*-
from .mockup import mockup_recursive_5
from nose.tools import istest
from .compmake_test import CompmakeTest


@istest
class TestParmakeNewProcess(CompmakeTest):

    # TODO: parmake_pool
    def test_parmake_new_process(self):
        mockup_recursive_5(self.cc)
        self.assert_cmd_success('parmake recurse=1 new_process=1;ls')

    # TODO: parmake_pool
    def test_make_new_process(self):
        mockup_recursive_5(self.cc)
        self.assert_cmd_success('make recurse=1 new_process=1;ls')

