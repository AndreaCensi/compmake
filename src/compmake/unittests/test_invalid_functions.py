# -*- coding: utf-8 -*-
import pytest
from .pytest_base import CompmakeTestBase
from ..exceptions import UserError


def uses_nested(context):
    def f1():
        pass

    context.comp(f1)


def uses_lambda(context):
    context.comp(lambda x: x, 1)


class TestInvalidFunctions(CompmakeTestBase):

    def test_invalid_function_nested(self):
        with pytest.raises(UserError):
            uses_nested(self.cc)

    def test_invalid_function_lambda(self):
        with pytest.raises(UserError):
            uses_lambda(self.cc)