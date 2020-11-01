from typing import Callable
from .. import set_compmake_status, CompmakeConstants
from .compmake_test import CompmakeTest
from nose.tools import istest


def f1() -> Callable:
    print("done")
    return lambda _: None


@istest
class TestUnpickable(CompmakeTest):
    def mySetUp(self) -> None:
        # TODO: use tmp dir
        set_compmake_status(CompmakeConstants.compmake_status_embedded)

    def test_unpickable_result(self) -> None:
        self.comp(f1)
        self.cc.batch_command("clean")

        self.assert_cmd_fail("make")
        # since dill implemented
        # self.assert_cmd_success('make')
