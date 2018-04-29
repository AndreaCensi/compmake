# -*- coding: utf-8 -*-
from nose.tools import istest
from compmake.unittests.compmake_test import CompmakeTest
from compmake.unittests.mockup_dynamic_4 import mockup_dyn4
 
 
 
@istest
class TestDynamic4(CompmakeTest):
 
    def test_dynamic4(self):
        mockup_dyn4(self.cc)
        self.assert_cmd_success('ls')
        self.assert_cmd_success('parmake recurse=1 echo=1')
        self.assert_cmd_success('ls')
        self.assert_cmd_success('details schedule')
        self.assert_cmd_success('details report')
        self.assert_cmd_success('clean')
        self.assert_cmd_success('ls')
        self.assert_cmd_success('parmake recurse=1 echo=1')
         

 
    def test_dynamic4b(self):
        mockup_dyn4(self.cc)
        self.assert_cmd_success('ls')
        self.assert_cmd_success('parmake recurse=1 echo=1')
        self.assert_cmd_success('ls')
        self.assert_cmd_success('details schedule')
        self.assert_cmd_success('details report')
        self.assert_cmd_success('clean schedule')
        self.assert_cmd_success('ls')
        self.assert_cmd_success('parmake recurse=1 echo=1')

    def test_dynamic4c(self):
        mockup_dyn4(self.cc)
        self.assert_cmd_success('ls')
        self.assert_cmd_success('parmake recurse=1 echo=1')
        self.assert_cmd_success('ls')
        self.assert_cmd_success('details schedule')
        self.assert_cmd_success('details report')
        self.assert_cmd_success('clean report')
        self.assert_cmd_success('ls')
        self.assert_cmd_success('parmake recurse=1 echo=1')
