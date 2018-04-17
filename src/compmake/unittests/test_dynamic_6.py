# -*- coding: utf-8 -*-
from .compmake_test import CompmakeTest
from compmake import Context
from compmake.jobs import direct_children, get_job, jobs_defined
from compmake.storage.filesystem import StorageFilesystem
from compmake.ui.ui import clean_other_jobs
from nose.tools import istest
from compmake.structures import Cache
from compmake.jobs.manager import check_job_cache_state
from compmake.exceptions import CompmakeBug

def g2(): 
    print('returning g2')
    return 'fd-gd-g2'

def gd(context):
    context.comp(g2)

def fd(context):
    return context.comp_dynamic(gd)

def i2():
    return 'hd-id-i2'

def id(context):  # @ReservedAssignment
    context.comp(i2)
    
def hd(context):
    return context.comp_dynamic(id)

def summary(res):
    pass
    
def mockup6(context, both):
    res = []
    res.append(context.comp_dynamic(fd))
    if both:
        res.append(context.comp_dynamic(hd))
    context.comp(summary, res)
        
 
@istest
class TestDynamic6(CompmakeTest):
 
    def test_dynamic6(self):
        
        # first define with job and run
        mockup6(self.cc, both=True)
        db = self.db
        
        self.assertRaises(CompmakeBug, jobs_defined, job_id='hd', db=db)
        
        self.assert_cmd_success('make recurse=1')
        check_job_cache_state(job_id='hd', states=[Cache.DONE], db=db)
        self.assertEqual(jobs_defined(job_id='hd', db=db),
                         set(['hd-id']))
        
        # self.assert_cmd_success('graph compact=0 color=0 '
        #                         'cluster=1 filter=dot')
        
        self.assertJobsEqual('all', ['fd', 'fd-gd', 'fd-gd-g2',  
                                     'hd', 'hd-id', 'hd-id-i2', 
                                     'summary'])
        self.assertJobsEqual('done',  ['fd', 'fd-gd', 'fd-gd-g2',  
                                       'hd', 'hd-id', 'hd-id-i2', 
                                       'summary'])
        
        # now redo it 
        self.db = StorageFilesystem(self.root, compress=True)
        self.cc = Context(db=self.db)
        
        print('running again with both=False')
        mockup6(self.cc, both=False)
        clean_other_jobs(context=self.cc)
        
        self.assertJobsEqual('all', ['fd', 'fd-gd', 'fd-gd-g2', 
                                     'summary'])
        
        job=  get_job('summary', self.db)
        print('job.children: %s' % job.children)
        print('job.dynamic_children: %s' % job.dynamic_children)
        self.assertEqual(job.dynamic_children, {'fd': set(['fd-gd'])})
        self.assertEqualSet(direct_children('summary', self.db), ['fd', 'fd-gd'])
        self.assert_cmd_success('ls')

        self.assert_cmd_success('make recurse=1')
        self.assertJobsEqual('all',  ['fd', 'fd-gd', 'fd-gd-g2', 'summary'])
        self.assertJobsEqual('done', ['fd', 'fd-gd', 'fd-gd-g2', 'summary']) 
        
