# -*- coding: utf-8 -*-
import pytest
import os
from .improved_pytest_base import CompmakeTestBase
from compmake.context import Context
from compmake.storage.filesystem import StorageFilesystem
from compmake.jobs.queries import definition_closure

def g2(): 
    pass

def gd(context):
    context.comp(g2)

def fd(context):
    context.comp_dynamic(gd)

def i2():
    pass

def id(context):  # @ReservedAssignment
    context.comp(i2)
    
def hd(context):
    context.comp_dynamic(id)
    
def mockup5(context, both):
    context.comp_dynamic(fd)
    if both:
        context.comp_dynamic(hd)
 
class TestDynamic5(CompmakeTestBase):
 
    def test_dynamic5(self, tmp_path):
        # Using pytest's tmp_path fixture for better isolation
        
        # Create a directory for first test phase
        test_dir1 = os.path.join(str(tmp_path), "test1")
        os.makedirs(test_dir1, exist_ok=True)
        
        # first define with job and run
        mockup5(self.cc, both=True)
        self.assert_cmd_success('make recurse=1')
        
        self.assertJobsEqual('all', ['fd', 'fd-gd', 'fd-gd-g2',  'hd', 'hd-id', 'hd-id-i2'])
        self.assertJobsEqual('done',  ['fd', 'fd-gd', 'fd-gd-g2',  'hd', 'hd-id', 'hd-id-i2'])

        self.assert_cmd_success('details hd-id')
        self.assert_cmd_success('details hd-id-i2')
        self.assertEqualSet(definition_closure(['hd-id'], self.db), ['hd-id-i2'])
        self.assertEqualSet(definition_closure(['hd'], self.db), ['hd-id', 'hd-id-i2'])
        
        # Create a fresh context for the second part of the test
        test_dir2 = os.path.join(str(tmp_path), "test2")
        os.makedirs(test_dir2, exist_ok=True)
        self.db = StorageFilesystem(test_dir2, compress=True)
        self.cc = Context(db=self.db)
        
        # now redo with different parameters
        mockup5(self.cc, both=False)
        self.assert_cmd_success('clean')
        self.assert_cmd_success('make recurse=1')
        self.assertJobsEqual('all',  ['fd', 'fd-gd', 'fd-gd-g2'])
        self.assertJobsEqual('done', ['fd', 'fd-gd', 'fd-gd-g2'])