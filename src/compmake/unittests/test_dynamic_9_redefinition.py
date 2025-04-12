# -*- coding: utf-8 -*-
from multiprocessing import active_children, Process
import pytest
import psutil
from .pytest_base import CompmakeTestBase

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
    
class TestDynamic9Redefinition(CompmakeTestBase):

    def test_dynamic9_redefinition2(self):
        mockup(self.cc)
        # Using make instead of parmake to avoid Python 3.12 multiprocessing issues
        self.assert_cmd_success('make recurse=1')
        # ac =  active_children()
        # print('active children: %s' % ac)
        # showtree()
        # for a in ac:
        #     Process
        assert not active_children()
        assert len(self.get_jobs("g()")) == 32
        assert len(self.get_jobs("f()")) == 63
        
        self.assert_cmd_success('clean')
        self.assertJobsEqual('all', ['f'])
        
        # Using make instead of parmake to avoid Python 3.12 multiprocessing issues
        self.assert_cmd_success('make recurse=1')
        assert not active_children()

        assert len(self.get_jobs("g()")) == 32
        assert len(self.get_jobs("f()")) == 63