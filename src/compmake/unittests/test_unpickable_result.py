# -*- coding: utf-8 -*-
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

    def test_unpickable_result(self):
        self.comp(f1)
        self.cc.batch_command('clean')
        
        self.assert_cmd_fail('make')
        
