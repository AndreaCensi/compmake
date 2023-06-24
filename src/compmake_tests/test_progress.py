import unittest

from compmake import init_progress_tracking, progress
from zuper_commons.test_utils import assert_raises, known_failure, my_assert_equal, istest


@istest
class TestProgress(unittest.TestCase):
    def stack_update(self, stack) -> None:
        # print "found %s" % stack
        self.stack = stack

    def assert_stack_len(self, d) -> None:
        my_assert_equal(d, len(self.stack))

    def setUp(self) -> None:
        init_progress_tracking(self.stack_update)

    def test_bad(self) -> None:
        """Many ways to call it in the wrong way."""
        with assert_raises(ValueError):
            progress("task", 1)  # type: ignore

    @known_failure
    def test_hierarchy_flat(self) -> None:
        """Testing basic case."""
        init_progress_tracking(lambda _: None)
        self.assert_stack_len(0)
        progress("A", (0, 2))
        self.assert_stack_len(1)
        progress("A", (1, 2))
        self.assert_stack_len(1)

    @known_failure
    def test_hierarchy_flat2(self) -> None:
        data = {}

        def mystack(x) -> None:
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
