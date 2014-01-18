from .. import set_compmake_status, CompmakeConstants
from .compmake_test import CompmakeTest
from nose.tools import istest


def f1():
    print("done")
    return lambda x: None #@UnusedVariable


@istest
class TestUnpickable(CompmakeTest):

    def mySetUp(self):
        # TODO: use tmp dir
        set_compmake_status(CompmakeConstants.compmake_status_embedded)

    def test_unpickable(self):
        res = self.add_and_execute(f1)
        self.assertNotEqual(res, 0)

    def add_and_execute(self, function):
        self.comp(function)
        self.cc.batch_command('clean')
        return self.cc.batch_command('make')
