# -*- coding: utf-8 -*-
import pytest
import os
from compmake import Context, StorageFilesystem
from compmake.jobs.storage import all_jobs
from compmake.state import set_compmake_config
from compmake.ui.visualization import info


def g():
    pass


def h():
    pass


class TestBase:
    @pytest.fixture(autouse=True)
    def setup_method(self, tmp_path):
        # Use pytest's tmp_path fixture for test isolation
        self.test_dir = tmp_path

    def all_jobs(self, root):
        """ Returns the list of jobs corresponding to the given expression. """
        db = StorageFilesystem(root, compress=True)
        return sorted(list(all_jobs(db)))


class TestCleaning1(TestBase):
    
    def test_cleaning_other(self, tmp_path):
        # Use a unique path for each test
        root = os.path.join(str(tmp_path), "test_cleaning_other")
        os.makedirs(root, exist_ok=True)
        
        self.run_first(root)
        jobs1 = self.all_jobs(root)
        assert jobs1 == ['g', 'h']
        self.run_second(root)
        jobs2 = self.all_jobs(root)
        assert jobs2 == ['g']
    
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
     

class TestCleaning2(TestBase):
    
    def test_cleaning2(self, tmp_path):
        # Use a unique path for each test
        root = os.path.join(str(tmp_path), "test_cleaning2")
        os.makedirs(root, exist_ok=True)
        
        self.run_first(root)
        jobs1 = self.all_jobs(root)
        assert jobs1 == ['f', 'f-g', 'f-h']
        self.run_second(root)
        jobs2 = self.all_jobs(root)
        assert jobs2 == ['f', 'f-g']
    
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
        

class TestCleaning3(TestBase):
    """ Now with multi level """
    
    # Preserve configuration with fixture
    @pytest.fixture(autouse=True)
    def save_config(self):
        # Save original config and set for this test
        original_check_params = set_compmake_config('check_params', True)
        yield
        # Restore after test
        set_compmake_config('check_params', original_check_params)
    
    def test_cleaning3(self, tmp_path):
        # Use a unique path for each test
        root = os.path.join(str(tmp_path), "test_cleaning3")
        os.makedirs(root, exist_ok=True)
        
        self.run_first(root)
        jobs1 = self.all_jobs(root)
        assert jobs1 == ['e', 'f', 'f-g', 'f-h']
        self.run_second(root)
        jobs2 = self.all_jobs(root)
        assert jobs2 == ['e', 'f', 'f-g']
    
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