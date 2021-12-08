import unittest

from nose.tools import assert_raises, istest

from compmake import init_progress_tracking, progress
from zuper_commons.test_utils import known_failure, my_assert_equal as assert_equal


@istest
class TestProgress(unittest.TestCase):
    def stack_update(self, stack):
        # print "found %s" % stack
        self.stack = stack

    def assert_stack_len(self, d):
        assert_equal(d, len(self.stack))

    def setUp(self):
        init_progress_tracking(self.stack_update)

    def test_bad(self):
        """Many ways to call it in the wrong way."""
        assert_raises((ValueError,), progress, "task", 1)

    @known_failure
    def test_hierarchy_flat(self):
        """Testing basic case."""
        init_progress_tracking(lambda _: None)
        self.assert_stack_len(0)
        progress("A", (0, 2))
        self.assert_stack_len(1)
        progress("A", (1, 2))
        self.assert_stack_len(1)

    @known_failure
    def test_hierarchy_flat2(self):
        data = {}

        def mystack(x):
            data["stack"] = x

        init_progress_tracking(mystack)
        self.assert_stack_len(0)
        progress("A", (0, 2))
        self.assert_stack_len(1)
        progress("B", (0, 2))
        self.assert_stack_len(2)
        progress("B", (1, 2))
        self.assert_stack_len(2)
        progress("A", (1, 2))
        self.assert_stack_len(1)
