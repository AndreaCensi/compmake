import unittest
from compmake import progress
from compmake.jobs.progress import init_progress_tracking, stack

class TestProgress(unittest.TestCase):
    
    def test_bad(self):
        ''' Many ways to call it in the wrong way. '''
        self.assertRaises(ValueError, progress, 'task', 1)
    
    
    def test_hierarchy_flat(self):
        ''' Testing basic case. '''        
        init_progress_tracking(lambda stack:None)
        self.assertEqual(len(stack), 0)
        progress('A', (0, 2))
        self.assertEqual(len(stack), 1)
        progress('A', (1, 2))
        self.assertEqual(len(stack), 1)

    def test_hierarchy_flat(self):        
        init_progress_tracking(lambda stack:None)
        self.assertEqual(len(stack), 0)
        progress('A', (0, 2))
        self.assertEqual(len(stack), 1)
        progress('B', (0, 2))
        self.assertEqual(len(stack), 2)
        progress('B', (1, 2))
        self.assertEqual(len(stack), 2)
        progress('A', (1, 2))
        self.assertEqual(len(stack), 1)
