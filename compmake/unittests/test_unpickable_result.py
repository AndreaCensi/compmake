import unittest
from compmake.structures import SerializationError


def f1():
    return lambda x: None

class TestUnpickable(unittest.TestCase):
    
    def test_unpickable(self):
        
        self.assertRaises(SerializationError, self.add_and_execute, f1)
        

    def add_and_execute(self, function):
        from compmake import comp, batch_command
        comp(function)
        batch_command('make')
