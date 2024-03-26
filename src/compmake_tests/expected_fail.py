import functools

import unittest


def expected_failure(test):
    @functools.wraps(test)
    def inner(*args, **kwargs):
        try:
            test(*args, **kwargs)
        except Exception:
            raise unittest.SkipTest
        else:
            raise AssertionError("Failure expected")

    return inner
