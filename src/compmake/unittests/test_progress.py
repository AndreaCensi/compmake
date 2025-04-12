# -*- coding: utf-8 -*-
import pytest
from ..jobs import init_progress_tracking
from compmake import progress
from contracts import ContractNotRespected


class TestProgress:

    def setup_method(self):
        self.stack = None
        init_progress_tracking(self.stack_update)

    def stack_update(self, stack):
        #print "found %s" % stack
        self.stack = stack

    def assert_stack_len(self, d):
        assert d == len(self.stack)

    def test_bad(self):
        """ Many ways to call it in the wrong way. """
        with pytest.raises((ValueError, ContractNotRespected)):
            progress('task', 1)

    @pytest.mark.skip(reason="Known failure, needs fixing")
    def test_hierarchy_flat(self):
        """ Testing basic case. """
        init_progress_tracking(lambda _: None)
        self.assert_stack_len(0)
        progress('A', (0, 2))
        self.assert_stack_len(1)
        progress('A', (1, 2))
        self.assert_stack_len(1)

    @pytest.mark.skip(reason="Known failure, needs fixing")
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