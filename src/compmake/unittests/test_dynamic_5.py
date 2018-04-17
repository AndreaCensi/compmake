# -*- coding: utf-8 -*-
from compmake.context import Context
from compmake.storage.filesystem import StorageFilesystem
from compmake.unittests.compmake_test import CompmakeTest
from nose.tools import istest
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
 
@istest
class TestDynamic5(CompmakeTest):
 
    def test_dynamic5(self):
        
        # first define with job and run
        mockup5(self.cc, both=True)
        self.assert_cmd_success('make recurse=1')
        
        self.assertJobsEqual('all', ['fd', 'fd-gd', 'fd-gd-g2',  'hd', 'hd-id', 'hd-id-i2'])
        self.assertJobsEqual('done',  ['fd', 'fd-gd', 'fd-gd-g2',  'hd', 'hd-id', 'hd-id-i2'])

        self.assert_cmd_success('details hd-id')
        self.assert_cmd_success('details hd-id-i2')
        self.assertEqualSet(definition_closure(['hd-id'], self.db), ['hd-id-i2'])
        self.assertEqualSet(definition_closure(['hd'], self.db), ['hd-id', 'hd-id-i2'])        
        # now redo it 
        self.db = StorageFilesystem(self.root, compress=True)
        self.cc = Context(db=self.db)
        
        mockup5(self.cc, both=False)
        self.assert_cmd_success('clean')
        self.assert_cmd_success('make recurse=1')
        self.assertJobsEqual('all',  ['fd', 'fd-gd', 'fd-gd-g2'])
        self.assertJobsEqual('done', ['fd', 'fd-gd', 'fd-gd-g2']) 
