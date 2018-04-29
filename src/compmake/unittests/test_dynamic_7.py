# -*- coding: utf-8 -*-
from .compmake_test import CompmakeTest
from nose.tools import istest
from compmake.exceptions import CompmakeDBError

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
        self.assert_cmd_success('make recurse=1; ls')
        
        # check that g2 is up to date
        self.assertEqual(self.up_to_date('fd-gd-g2'), True)
        
        # now clean its parent
        self.assert_cmd_success('clean fd')
        
        # job does not exist anynmore
        self.assertRaises(CompmakeDBError, self.up_to_date, 'fd-gd-g2')
    
    
    def test_dynamic7_invalidate(self):
        # first define with job and run
        mockup7(self.cc)
        self.assert_cmd_success('make recurse=1; ls')
        
        # check that g2 is up to date
        self.assertEqual(self.up_to_date('fd-gd-g2'), True)
        
        # now invalidate the parent
        self.assert_cmd_success('invalidate fd')
        
        # job exists but not up to date
        self.assertEqual(self.up_to_date('fd-gd-g2'), False)
