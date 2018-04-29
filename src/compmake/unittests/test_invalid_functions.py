# -*- coding: utf-8 -*-
from nose.tools import istest

from compmake.unittests.compmake_test import CompmakeTest

from ..exceptions import UserError


def uses_nested(context):
    def f1():
        pass

    context.comp(f1)


def uses_lambda(context):

    context.comp(lambda x: x, 1)


@istest
class TestInvalidFunctions(CompmakeTest):

    def test_invalid_function_nested(self):
        self.assertRaises(UserError, uses_nested, self.cc)

    def test_invalid_function_lambda(self):
        self.assertRaises(UserError, uses_lambda, self.cc)
