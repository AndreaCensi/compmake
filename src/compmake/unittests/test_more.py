# -*- coding: utf-8 -*-
from . import CompmakeTest
from ..jobs import direct_children, direct_parents, make
from ..exceptions import UserError
from nose.tools import istest


def f1(*arg, **kwargs):
    """ Generic function """
    pass


def f2(*arg, **kwargs):
    """ Generic function """
    pass


def failing():
    """ A function that raises an exception """
    raise TypeError()


def uses_id(a, b, job_id):
    """ A function with a job_id arguement """
    pass


@istest
class Test1(CompmakeTest):
    def mySetUp(self):
        pass

    def testAdding(self):
        self.comp(f1)
        self.assertTrue(True)

    def testID(self):
        """ Check that the job id is correctly parsed """
        job_id = 'terminus'
        c = self.comp(f1, job_id=job_id)
        self.assertEqual(c.job_id, job_id)
        make(job_id, context=self.cc)
        self.assertTrue(True)

    def testID2(self):
        """ Make sure we set up a warning if the job_id key
            is already used """
        self.assertTrue(self.comp(f1, job_id='ciao'))
        self.assertRaises(UserError, self.comp, f1, job_id='ciao')

    def testDep(self):
        """ Testing advanced dependencies discovery """
        cf1 = self.comp(f1)
        cf2 = self.comp(f2, cf1)
        self.assertTrue(cf1.job_id in direct_children(cf2.job_id, db=self.db))
        self.assertTrue(cf2.job_id in direct_parents(cf1.job_id, db=self.db))

    def testDep2(self):
        """ Testing advanced dependencies discovery (double) """
        cf1 = self.comp(f1)
        cf2 = self.comp(f2, cf1, cf1)
        self.assertTrue(cf1.job_id in direct_children(cf2.job_id, db=self.db))
        self.assertEqual(1, len(direct_children(cf2.job_id, db=self.db)))
        self.assertEqual(1, len(direct_parents(cf1.job_id, db=self.db)))

    def testDep3(self):
        """ Testing advanced dependencies discovery in dicts"""
        cf1 = self.comp(f1)
        cf2 = self.comp(f2, [1, {'ciao': cf1}])
        self.assertTrue(cf1.job_id in direct_children(cf2.job_id, db=self.db))
        self.assertTrue(cf2.job_id in direct_parents(cf1.job_id, db=self.db))

    def testJOBparam(self):
        """ We should issue a warning if job_id is used
            as a parameter in the function """
        self.comp(uses_id)
        self.assertRaises(UserError, self.comp, uses_id, job_id='myjobid')



