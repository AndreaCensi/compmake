# -*- coding: utf-8 -*-
from nose.tools import istest

from .compmake_test import CompmakeTest


def f(a):
    print('f()')
    if not a == 2:
        raise ValueError('Expected 2, not %s' % a)


def g(context):
    """ This function returns a Promise to another job. """
    print('g()')
    return context.comp(g_delegated)


def g_delegated():
    print('g_delegated()')
    return 1 + 1


@istest
class TestDelegation(CompmakeTest):

    def test_delegation_1(self):
        context = self.cc

        g_res = context.comp_dynamic(g)
        context.comp(f, g_res)

        self.assert_cmd_success('ls')
        self.assert_cmd_success('stats')
        self.assert_cmd_success('make g()')
        self.assert_cmd_success('ls')
        self.assert_cmd_success('make g_delegated()')
        

    def test_delegation_2(self):
            context = self.cc
    
            g_res = context.comp_dynamic(g)
            context.comp(f, g_res)
    
            self.assert_cmd_success('ls')
            self.assert_cmd_success('stats')
            self.assert_cmd_success('make')
        
        
