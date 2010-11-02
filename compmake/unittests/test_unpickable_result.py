import unittest
from compmake.structures import SerializationError
from compmake.storage import use_filesystem
from compmake.jobs.storage import set_namespace
from compmake import storage


def f1():
    print "done"
    return lambda x: None

class TestUnpickable(unittest.TestCase):
    
    def setUp(self):
        use_filesystem('unpickable')
        set_namespace('unpickable')
        for key in storage.db.keys('*'):
            storage.db.delete(key)
    
    
    def test_unpickable(self):
        
        self.assertRaises(SerializationError, self.add_and_execute, f1)
        

    def add_and_execute(self, function):
        from compmake import comp, batch_command
        comp(function)
        
        batch_command('clean')
        batch_command('make all')
