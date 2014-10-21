from .compmake_test import CompmakeTest
from compmake import Context
from compmake.jobs import direct_children, get_job, jobs_defined
from compmake.storage.filesystem import StorageFilesystem
from compmake.ui.ui import clean_other_jobs
from nose.tools import istest

def g2(): 
    return 'g2'

def gd(context):
    context.comp(g2)

def fd(context):
    return context.comp_dynamic(gd)

def i2():
    return 'i2'

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
        
        self.assertRaises(ValueError, jobs_defined, job_id='hd', db=self.db)
        
        self.assert_cmd_success('make recurse=1')
        self.assertEqual(jobs_defined(job_id='hd', db=self.db),
                         set(['id']))
        
        self.assert_cmd_success('graph compact=0 color=0 '
                                'cluster=1 filter=dot')
        
        self.assertJobsEqual('all', ['fd', 'gd', 'g2',  
                                     'hd', 'id', 'i2', 
                                     'summary'])
        self.assertJobsEqual('done',  ['fd', 'gd', 'g2',  
                                       'hd', 'id', 'i2', 
                                       'summary'])
        
        # now redo it 
        self.db = StorageFilesystem(self.root, compress=True)
        self.cc = Context(db=self.db)
        
        print('running again with both=False')
        mockup6(self.cc, both=False)
        clean_other_jobs(context=self.cc)
        
        self.assertJobsEqual('all', ['fd', 'gd', 'g2', 
                                     'summary'])
        
        job=  get_job('summary', self.db)
        print('job.children: %s' % job.children)
        print('job.dynamic_children: %s' % job.dynamic_children)
        self.assertEqual(job.dynamic_children, {'fd': set(['gd'])})
        self.assertEqualSet(direct_children('summary', self.db), ['fd', 'gd'])
        self.assert_cmd_success('ls')
#         self.assert_cmd_success('clean')
        self.assert_cmd_success('make recurse=1')
        self.assertJobsEqual('all',  ['fd', 'gd', 'g2', 'summary'])
        self.assertJobsEqual('done', ['fd', 'gd', 'g2', 'summary']) 
        
        