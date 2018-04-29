# -*- coding: utf-8 -*-
from compmake import Context, StorageFilesystem
from compmake.jobs.storage import all_jobs
from compmake.state import set_compmake_config
from compmake.ui.visualization import info
from nose.tools import istest
from tempfile import mkdtemp
import unittest


def g():
    pass

def h():
    pass

@istest
class Utils(unittest.TestCase):
    def all_jobs(self, root):
        """ Returns the list of jobs corresponding to the given expression. """
        db = StorageFilesystem(root, compress=True)
        return sorted(list(all_jobs(db)))

    
@istest
class TestCleaning1(Utils):
    
    def test_cleaning_other(self):
        root = mkdtemp()
        self.run_first(root)
        jobs1 = self.all_jobs(root)
        self.assertEqual(jobs1, ['g','h'])
        self.run_second(root)
        jobs2 = self.all_jobs(root)
        self.assertEqual(jobs2, ['g'])
    
    def run_first(self, root):
        db = StorageFilesystem(root, compress=True)
        cc = Context(db=db)
        # 
        cc.comp(g, job_id='g')
        cc.comp(h, job_id='h')
        cc.batch_command('make')
        
    def run_second(self, root):
        db = StorageFilesystem(root, compress=True)
        cc = Context(db=db)
        # 
        cc.comp(g, job_id='g')
        cc.batch_command('make')
    
        

def f1(context):
    context.comp(g)
    context.comp(h)
 
def f2(context):
    context.comp(g)
     

@istest
class TestCleaning2(Utils):
    
    def test_cleaning2(self):
        root = mkdtemp()
        self.run_first(root)
        jobs1 = self.all_jobs(root)
        self.assertEqual(jobs1, ['f', 'f-g', 'f-h'])
        self.run_second(root)
        jobs2 = self.all_jobs(root)
        self.assertEqual(jobs2, ['f', 'f-g'])
    
    def run_first(self, root):
        info('run_first()')
        db = StorageFilesystem(root, compress=True)
        cc = Context(db=db)
        # 
        cc.comp_dynamic(f1, job_id='f')
        cc.batch_command('make recurse=1')
        
    def run_second(self, root):
        info('run_second()')
        db = StorageFilesystem(root, compress=True)
        cc = Context(db=db)
        # 
        cc.comp_dynamic(f2, job_id='f')
        cc.batch_command('clean;make recurse=1')
    



def e1(context):
    context.comp_dynamic(f1, job_id='f')
    
def e2(context):
    context.comp_dynamic(f2, job_id='f')
        

@istest
class TestCleaning3(Utils):
    """ Now with multi level """
    
#     @expected_failure
    def test_cleaning3(self):
        set_compmake_config('check_params', True)
        root = mkdtemp()
        self.run_first(root)
        jobs1 = self.all_jobs(root)
        self.assertEqual(jobs1, ['e', 'f', 'f-g', 'f-h'])
        self.run_second(root)
        jobs2 = self.all_jobs(root)
        self.assertEqual(jobs2, ['e', 'f', 'f-g'])
    
    def run_first(self, root):
        print('run_first()')
        db = StorageFilesystem(root, compress=True)
        cc = Context(db=db)
        # 
        cc.comp_dynamic(e1, job_id='e')
        cc.batch_command('make recurse=1; ls')
        
    def run_second(self, root):
        print('run_second()')
        db = StorageFilesystem(root, compress=True)
        cc = Context(db=db)
        # 
        cc.comp_dynamic(e2, job_id='e')
        cc.batch_command('details e;clean;ls;make recurse=1')
