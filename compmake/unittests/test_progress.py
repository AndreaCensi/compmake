import unittest
from compmake import progress
from compmake.jobs.progress import init_progress_tracking

class TestProgress(unittest.TestCase):
    
    def stack_update(self, stack):
        print "found %s" % stack
        self.stack = stack
        
    def assert_stack_len(self, d):
        self.assertEqual(d, len(self.stack))
        
    def setUp(self):
        init_progress_tracking(self.stack_update)
    
    def test_bad(self):
        ''' Many ways to call it in the wrong way. '''
        self.assertRaises(ValueError, progress, 'task', 1)
    
    
    def test_hierarchy_flat(self):
        ''' Testing basic case. '''        
        init_progress_tracking(lambda stack:None)
        self.assert_stack_len(0)
        progress('A', (0, 2))
        self.assert_stack_len(1)
        progress('A', (1, 2))
        self.assert_stack_len(1)
        
    def test_hierarchy_flat2(self):
        data = {}
        def mystack(x):     
            data['stack'] = x
        init_progress_tracking(mystack)
        self.assert_stack_len(0)
        progress('A', (0, 2))
        self.assert_stack_len(1) 
        progress('B', (0, 2))
        self.assert_stack_len(2) 
        progress('B', (1, 2))
        self.assert_stack_len(2)
        progress('A', (1, 2))
        self.assert_stack_len(1) 
