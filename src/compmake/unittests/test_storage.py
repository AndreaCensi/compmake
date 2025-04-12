# -*- coding: utf-8 -*-
import pytest
from compmake.utils import wildcard_to_regexp
from .pytest_base import CompmakeTestBase


class TestSimple(CompmakeTestBase):
    def mySetUp(self):
        pass

    def test_exists1(self):
        key = 'not-existent'
        assert not key in self.db

    def test_exists2(self):
        k = 'ciao'
        v = {'complex': 123}
        db = self.db
        if k in db:
            del db[k]
        assert not k in db
        db[k] = v
        assert k in db
        del db[k]
        assert not k in db
        db[k] = v
        del db[k]
        assert not k in db

    def test_search(self):
        db = self.db

        def search(pattern):
            r = wildcard_to_regexp(pattern)
            for k in db.keys():
                if r.match(k):
                    yield k

        assert list(search('*')) == []
        db['key1'] = 1
        db['key2'] = 1
        assert list(search('ciao*')) == []
        assert list(search('key1')) == ['key1']
        assert list(search('*1')) == ['key1']
        assert list(search('d*1')) == []