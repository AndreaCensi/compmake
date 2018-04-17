# -*- coding: utf-8 -*-
from nose.tools import istest

from .compmake_test import CompmakeTest

def f():
    pass

def g(context):
    context.comp(f, job_id='ciao') # this will become ciao-0
    
    
@istest
class TestDynamic3(CompmakeTest):
    def test_dynamic3(self):
        context = self.cc
        context.comp(f, job_id='ciao')
        self.assert_cmd_success('ls')
        self.assert_cmd_success('make')
        context.comp_dynamic(g, job_id='g')
        self.assert_cmd_success('make g')

