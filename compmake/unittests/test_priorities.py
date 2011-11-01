import unittest
from ..storage import use_filesystem
from ..jobs import set_namespace
from .. import storage, compmake_status_embedded, set_compmake_status

def bottom():
    TestOrder.order.append('bottom')

def bottom2():
    TestOrder.order.append('bottom2')

def top(x): #@UnusedVariable
    TestOrder.order.append('top')

class TestOrder(unittest.TestCase):
    
    order = []
    
    def setUp(self):
        set_compmake_status(compmake_status_embedded)
        use_filesystem('priorities')
        set_namespace('priorities')
        # make sure everything was clean
        for key in storage.db.keys('*'):
            storage.db.delete(key)
    
        # clear the variable holding the result
        TestOrder.order = []
    
    def test_order(self):
        from compmake import comp, batch_command
        # add two copies
        comp(top, comp(bottom))
        comp(top, comp(bottom))
        
        batch_command('clean')
        batch_command('make')

        self.assertEqual(['bottom', 'top', 'bottom', 'top'], TestOrder.order)


    def test_order_2(self):
        from compmake import comp, batch_command
        # choose wisely here
        comp(top, comp(bottom))
        comp(top, comp(bottom))
        comp(bottom2)
        
        batch_command('clean')
        batch_command('make')

        self.assertEqual(['bottom2', 'bottom', 'top', 'bottom', 'top'], TestOrder.order)
        
    def test_order_3(self):
        from compmake import comp, batch_command
        # choose wisely here
        comp(top, comp(bottom2))
        comp(bottom)
        comp(top, comp(bottom2))
        
        batch_command('clean')
        batch_command('make')

        self.assertEqual(['bottom', 'bottom2', 'top', 'bottom2', 'top'], TestOrder.order)
