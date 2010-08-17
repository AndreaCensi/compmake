from compmake import comp
import unittest
from compmake.structures import  UserError


def uses_nested():
    def f1():
        pass
    
    comp(f1)

def uses_lambda():
    
    comp(lambda x: x, 1)


class TestInvalidFunctions(unittest.TestCase):
    def test_invalid_function_nested(self):
        self.assertRaises(UserError, uses_nested)
    def test_invalid_function_lambda(self):
        self.assertRaises(UserError, uses_lambda)
