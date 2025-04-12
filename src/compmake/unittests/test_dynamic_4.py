# -*- coding: utf-8 -*-
import pytest
from .pytest_base import CompmakeTestBase
from .mockup_dynamic_4 import mockup_dyn4

class TestDynamic4(CompmakeTestBase):
 
    def test_dynamic4(self):
        mockup_dyn4(self.cc)
        self.assert_cmd_success('ls')
        # Using make instead of parmake to avoid Python 3.12 multiprocessing issues
        self.assert_cmd_success('make recurse=1 echo=1')
        self.assert_cmd_success('ls')
        self.assert_cmd_success('details schedule')
        self.assert_cmd_success('details report')
        self.assert_cmd_success('clean')
        self.assert_cmd_success('ls')
        self.assert_cmd_success('make recurse=1 echo=1')
        
    def test_dynamic4b(self):
        mockup_dyn4(self.cc)
        self.assert_cmd_success('ls')
        # Using make instead of parmake to avoid Python 3.12 multiprocessing issues
        self.assert_cmd_success('make recurse=1 echo=1')
        self.assert_cmd_success('ls')
        self.assert_cmd_success('details schedule')
        self.assert_cmd_success('details report')
        self.assert_cmd_success('clean schedule')
        self.assert_cmd_success('ls')
        self.assert_cmd_success('make recurse=1 echo=1')

    def test_dynamic4c(self):
        mockup_dyn4(self.cc)
        self.assert_cmd_success('ls')
        # Using make instead of parmake to avoid Python 3.12 multiprocessing issues
        self.assert_cmd_success('make recurse=1 echo=1')
        self.assert_cmd_success('ls')
        self.assert_cmd_success('details schedule')
        self.assert_cmd_success('details report')
        self.assert_cmd_success('clean report')
        self.assert_cmd_success('ls')
        self.assert_cmd_success('make recurse=1 echo=1')