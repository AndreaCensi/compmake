from .. import set_compmake_status, CompmakeConstants
from ..structures import SerializationError
from .compmake_test import CompmakeTest
from nose.tools import  istest


def f1():
    print("done")
    return lambda x: None #@UnusedVariable


@istest
class TestUnpickable(CompmakeTest):

    def mySetUp(self):
        # TODO: use tmp dir
        set_compmake_status(CompmakeConstants.compmake_status_embedded)

    def test_unpickable(self):
        self.assertRaises(SerializationError, self.add_and_execute, f1)

    def add_and_execute(self, function):
        from compmake import comp, batch_command
        comp(function)
        batch_command('clean')
        batch_command('make')
