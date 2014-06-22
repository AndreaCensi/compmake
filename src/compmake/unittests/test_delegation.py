from nose.tools import istest

from .compmake_test import CompmakeTest


def f(a):
    if not a == 2:
        raise ValueError('Expected 2, not %s' % a)


def g(context):
    """ This function returns a Promise to another job. """
    return context.comp(g_delegated)


def g_delegated():
    return 1 + 1


@istest
class TestDelegation(CompmakeTest):

    def test_delegation_1(self):
        context = self.cc

        g_res = context.comp_dynamic(g)
        context.comp(f, g_res)

        self.assert_cmd_success('ls')

        self.assert_cmd_success('make')
#         res = self.cc.interpret_commands_wrap('make')
#
#
#         self.assert_cmd_success('check-consistency')
