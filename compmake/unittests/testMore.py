from compmake import comp
from compmake.structures import ParsimException, UserError
from compmake.process import make
import unittest


def f1(*arg,**kwargs):
    ''' Generic function '''
    pass

def f2(*arg,**kwargs):
    ''' Generic function '''
    pass

def failing():
    raise TypeError()

def uses_id(a,b,job_id):
    pass
    


class Test1(unittest.TestCase):
    
    def testAdding(self):
        comp(f1)
        self.assertTrue(True)
        
    def testID(self):
        ''' Check that the job id is correctly parsed '''
        job_id = 'terminus';
        c = comp(f1, job_id=job_id)
        self.assertEqual(c.job_id, job_id)
        make(job_id)
        self.assertTrue(True)
        
    def testID2(self):
        ''' Make sure we set up a warning if the job_id key
           is already used '''
        self.assertTrue( comp(f1, job_id='ciao'))
        self.assertRaises(UserError, comp, f1, job_id='ciao')
        
    def testDep(self):
        ''' Testing advanced dependencies discovery '''
        cf1 = comp(f1)
        cf2 = comp(f2, cf1)
        self.assertTrue(cf1 in cf2.depends)
        self.assertTrue(cf2 in cf1.needed_by)

    def testDep2(self):
        ''' Testing advanced dependencies discovery (double) '''
        cf1 = comp(f1)
        cf2 = comp(f2, cf1, cf1)
        self.assertTrue(cf1 in cf2.depends)
        self.assertEqual(1, len(cf2.depends))
        self.assertEqual(1, len(cf1.needed_by))
        
    def testDep3(self):
        ''' Testing advanced dependencies discovery in dicts'''
        cf1 = comp(f1)
        cf2 = comp(f2, [1, {'ciao': cf1}])
        self.assertTrue(cf1 in cf2.depends)
        self.assertTrue(cf2 in cf1.needed_by)
      
    def testJOBparam(self):
        ''' We should issue a warning if job_id is used as a parameter in the function '''
        cf1 = comp(uses_id)
        self.assertRaises(UserError, comp, uses_id, job_id='myjobid' )
        
        
        