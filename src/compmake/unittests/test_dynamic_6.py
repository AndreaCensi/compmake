# -*- coding: utf-8 -*-
import pytest
import os
from .improved_pytest_base import CompmakeTestBase
from compmake import Context
from compmake.jobs import direct_children, get_job, jobs_defined
from compmake.storage.filesystem import StorageFilesystem
from compmake.ui.ui import clean_other_jobs
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
        
class TestDynamic6(CompmakeTestBase):
 
    def test_dynamic6(self, tmp_path):
        # Use a unique path for better isolation
        test_dir = os.path.join(str(tmp_path), "test_dynamic6")
        os.makedirs(test_dir, exist_ok=True)
        
        # first define with job and run
        mockup6(self.cc, both=True)
        db = self.db
        
        with pytest.raises(CompmakeBug):
            jobs_defined(job_id='hd', db=db)
        
        self.assert_cmd_success('make recurse=1')
        check_job_cache_state(job_id='hd', states=[Cache.DONE], db=db)
        assert jobs_defined(job_id='hd', db=db) == set(['hd-id'])
        
        # self.assert_cmd_success('graph compact=0 color=0 '
        #                         'cluster=1 filter=dot')
        
        self.assertJobsEqual('all', ['fd', 'fd-gd', 'fd-gd-g2',  
                                     'hd', 'hd-id', 'hd-id-i2', 
                                     'summary'])
        self.assertJobsEqual('done',  ['fd', 'fd-gd', 'fd-gd-g2',  
                                       'hd', 'hd-id', 'hd-id-i2', 
                                       'summary'])
        
        # Create a fresh context for the second part to ensure isolation
        test_dir2 = os.path.join(str(tmp_path), "test_dynamic6_2")
        os.makedirs(test_dir2, exist_ok=True)
        self.db = StorageFilesystem(test_dir2, compress=True)
        self.cc = Context(db=self.db)
        
        print('running again with both=False')
        mockup6(self.cc, both=False)
        clean_other_jobs(context=self.cc)
        
        self.assertJobsEqual('all', ['fd', 'summary'])
        
        job = get_job('summary', self.db)
        print('job.children: %s' % job.children)
        print('job.dynamic_children: %s' % job.dynamic_children)
        assert job.dynamic_children == {}
        self.assertEqualSet(direct_children('summary', self.db), ['fd'])
        self.assert_cmd_success('ls')

        self.assert_cmd_success('make recurse=1')
        self.assertJobsEqual('all',  ['fd', 'fd-gd', 'fd-gd-g2', 'summary'])
        self.assertJobsEqual('done', ['fd', 'fd-gd', 'fd-gd-g2', 'summary'])