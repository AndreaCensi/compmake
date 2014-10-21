from .compmake_test import CompmakeTest
from nose.tools import istest

def g2(): 
    return 'g2'

def gd(context):
    context.comp(g2)

def fd(context):
    return context.comp_dynamic(gd)

def mockup7(context):
    context.comp_dynamic(fd)
 
@istest
class TestDynamic7(CompmakeTest):
 
    
    def test_dynamic7(self):
        # first define with job and run
        mockup7(self.cc)
        self.assert_cmd_success('make recurse=1')
        
        # check that g2 is up to date
        self.assertEqual(self.up_to_date('g2'), True)
        
        # now clean its parent
        self.assert_cmd_success('clean fd')
        
        # now g2 should not be up to date
        self.assertEqual(self.up_to_date('g2'), False)
        