# -*- coding: utf-8 -*-
from ..jobs import init_progress_tracking
from compmake import progress
from contracts import ContractNotRespected
from nose.tools import istest, nottest
import unittest


@istest
class TestProgress(unittest.TestCase):

    def stack_update(self, stack):
        #print "found %s" % stack
        self.stack = stack

    def assert_stack_len(self, d):
        self.assertEqual(d, len(self.stack))

    def setUp(self):
        init_progress_tracking(self.stack_update)

    def test_bad(self):
        """ Many ways to call it in the wrong way. """
        self.assertRaises((ValueError, ContractNotRespected),
                          progress, 'task', 1)

    @nottest # FIXME, known failure
    def test_hierarchy_flat(self):
        """ Testing basic case. """
        init_progress_tracking(lambda _: None)
        self.assert_stack_len(0)
        progress('A', (0, 2))
        self.assert_stack_len(1)
        progress('A', (1, 2))
        self.assert_stack_len(1)

    @nottest # FIXME, known failure
    def test_hierarchy_flat2(self):
        data = {}

        def mystack(x):
            data['stack'] = x
        init_progress_tracking(mystack)
        self.assert_stack_len(0)
        progress('A', (0, 2))
        self.assert_stack_len(1)
        progress('B', (0, 2))
        self.assert_stack_len(2)
        progress('B', (1, 2))
        self.assert_stack_len(2)
        progress('A', (1, 2))
        self.assert_stack_len(1)
