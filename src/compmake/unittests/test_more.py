# -*- coding: utf-8 -*-
import pytest
from .pytest_base import CompmakeTestBase
from ..jobs import direct_children, direct_parents, make
from ..exceptions import UserError


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


class TestMore(CompmakeTestBase):
    def mySetUp(self):
        pass

    def test_adding(self):
        self.comp(f1)
        assert True

    def test_id(self):
        """ Check that the job id is correctly parsed """
        job_id = 'terminus'
        c = self.comp(f1, job_id=job_id)
        assert c.job_id == job_id
        make(job_id, context=self.cc)
        assert True

    def test_id2(self):
        """ Make sure we set up a warning if the job_id key
            is already used """
        assert self.comp(f1, job_id='ciao')
        with pytest.raises(UserError):
            self.comp(f1, job_id='ciao')

    def test_dep(self):
        """ Testing advanced dependencies discovery """
        cf1 = self.comp(f1)
        cf2 = self.comp(f2, cf1)
        assert cf1.job_id in direct_children(cf2.job_id, db=self.db)
        assert cf2.job_id in direct_parents(cf1.job_id, db=self.db)

    def test_dep2(self):
        """ Testing advanced dependencies discovery (double) """
        cf1 = self.comp(f1)
        cf2 = self.comp(f2, cf1, cf1)
        assert cf1.job_id in direct_children(cf2.job_id, db=self.db)
        assert 1 == len(direct_children(cf2.job_id, db=self.db))
        assert 1 == len(direct_parents(cf1.job_id, db=self.db))

    def test_dep3(self):
        """ Testing advanced dependencies discovery in dicts"""
        cf1 = self.comp(f1)
        cf2 = self.comp(f2, [1, {'ciao': cf1}])
        assert cf1.job_id in direct_children(cf2.job_id, db=self.db)
        assert cf2.job_id in direct_parents(cf1.job_id, db=self.db)

    def test_job_param(self):
        """ We should issue a warning if job_id is used
            as a parameter in the function """
        self.comp(uses_id)
        with pytest.raises(UserError):
            self.comp(uses_id, job_id='myjobid')