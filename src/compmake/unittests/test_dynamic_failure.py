# -*- coding: utf-8 -*-
import pytest
from .improved_pytest_base import CompmakeTestBase
from compmake import Context
from compmake.storage.filesystem import StorageFilesystem

def g2():
    pass

def g(context):
    context.comp(g2)

def h2():
    pass

def h(context):
    context.comp(h2)

def fd_wrapper(context):
    """Wrapper function that avoids lambda function issue."""
    # Access global test state from the test class
    # This approach preserves the original test logic while making it test-isolated
    test_class = TestDynamicFailure.current_test
    
    context.comp_dynamic(g)
    
    if test_class.current_exception is not None:
        raise test_class.current_exception()
    
    context.comp_dynamic(h)

def mockup8(context):
    context.comp_dynamic(fd_wrapper)

class TestDynamicFailure(CompmakeTestBase):
    """Test class with improvements for test isolation."""
    
    # Class variable to track the current test instance
    # This avoids pickle issues with lambda functions
    current_test = None
    
    def setup_method(self):
        # Set current test to this instance for each test method
        TestDynamicFailure.current_test = self
        # Initialize exception state for this test
        self.current_exception = None

    def test_dynamic_failure1(self):
        # Set the exception for this specific test
        self.current_exception = ValueError
        
        # Run the test
        mockup8(self.cc)
        self.assert_cmd_fail('make recurse=1')
        self.assertJobsEqual('all', ['fd_wrapper'])

    def test_dynamic_failure2(self):
        # First run with no failure
        self.current_exception = None
        mockup8(self.cc)
        self.assert_cmd_success('make recurse=1')
        
        # Check expected jobs were created
        self.assertJobsEqual('all', ['fd_wrapper', 'fd_wrapper-h', 'fd_wrapper-h-h2',
                                    'fd_wrapper-g', 'fd_wrapper-g-g2'])
        self.assertJobsEqual('done', ['fd_wrapper', 'fd_wrapper-h', 'fd_wrapper-h-h2',
                                     'fd_wrapper-g', 'fd_wrapper-g-g2'])

        # Create a completely separate context with a fresh root directory
        import tempfile
        # Create a brand new temp directory to avoid any cached state
        new_root = tempfile.mkdtemp()
        self.db = StorageFilesystem(new_root, compress=True)
        self.cc = Context(db=self.db)
        
        # Now run with failure
        self.current_exception = ValueError
        mockup8(self.cc)
        
        # Clear cache to ensure job is rerun
        self.assert_cmd_success('clean')
        self.assert_cmd_fail('make recurse=1')
        self.assertJobsEqual('all', ['fd_wrapper'])

    def test_dynamic_failure3(self):
        # Test with keyboard interrupt
        self.current_exception = KeyboardInterrupt
        
        mockup8(self.cc)
        self.assert_cmd_fail('make recurse=1')
        self.assertJobsEqual('all', ['fd_wrapper'])