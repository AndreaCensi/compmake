# -*- coding: utf-8 -*-
from multiprocessing import active_children

from nose.tools import istest
from compmake.unittests.compmake_test import CompmakeTest

def g(b1, b2):
    pass

def f(context, level): 
    if level == 0:
        context.comp(g, 1, 1)
    else:
        context.comp_dynamic(f, level-1)
        #if level >= 2 or random.random() < 0.5:
        context.comp_dynamic(f, level-1)
    
def mockup(context):
    context.comp_dynamic(f, 5)
    
@istest
class TestDynamic9(CompmakeTest):

    if False:
        def test_dynamic9_redefinition(self):
            mockup(self.cc)
            self.assert_cmd_success('make recurse=1')
                    
            self.assertEqual(len(self.get_jobs("g()")), 32)
            self.assertEqual(len(self.get_jobs("f()")), 63)
            
            self.assert_cmd_success('clean')
            self.assertJobsEqual('all', ['f'])
            
            self.assert_cmd_success('make recurse=1')
        
            self.assertEqual(len(self.get_jobs("g()")), 32)
            self.assertEqual(len(self.get_jobs("f()")), 63)
    
    def test_dynamic9_redefinition2(self):
        mockup(self.cc)
        self.assert_cmd_success('parmake recurse=1')
        assert not active_children()
        self.assertEqual(len(self.get_jobs("g()")), 32)
        self.assertEqual(len(self.get_jobs("f()")), 63)
        
        self.assert_cmd_success('clean')
        self.assertJobsEqual('all', ['f'])
        
        self.assert_cmd_success('parmake recurse=1')
        assert not active_children()

        self.assertEqual(len(self.get_jobs("g()")), 32)
        self.assertEqual(len(self.get_jobs("f()")), 63)
        
        
