# -*- coding: utf-8 -*-

from compmake.unittests.compmake_test import CompmakeTest
from nose.tools import istest


def g2():
    pass


def g(context):
    context.comp(g2)


def h2():
    pass


def h(context):
    context.comp(h2)


def fd(context):
    context.comp_dynamic(g)

    if TestDynamicFailure.do_fail is not None:
        raise TestDynamicFailure.do_fail()

    context.comp_dynamic(h)


def mockup8(context):
    context.comp_dynamic(fd)


@istest
class TestDynamicFailure(CompmakeTest):
    do_fail = False


    def test_dynamic_failure1(self):
        mockup8(self.cc)
        # run it
        TestDynamicFailure.do_fail = ValueError
        self.assert_cmd_fail('make recurse=1')
        # we have three jobs defined
        self.assertJobsEqual('all', ['fd'])

    def test_dynamic_failure2(self):
        mockup8(self.cc)
        # run it
        TestDynamicFailure.do_fail = None
        self.assert_cmd_success('make recurse=1')
        # we have three jobs defined
        self.assertJobsEqual('all', ['fd', 'fd-h', 'fd-h-h2',
                                     'fd-g', 'fd-g-g2'])
        self.assertJobsEqual('done', ['fd', 'fd-h', 'fd-h-h2',
                                      'fd-g', 'fd-g-g2'])

        TestDynamicFailure.do_fail = ValueError
        self.assert_cmd_success('invalidate fd')
        self.assert_cmd_success('stats')
        self.assert_cmd_fail('make')
        self.assertJobsEqual('all', ['fd'])


    def test_dynamic_failure3(self):
        mockup8(self.cc)
        # run it
        TestDynamicFailure.do_fail = KeyboardInterrupt
        self.assert_cmd_fail('make recurse=1')
        # we have three jobs defined
        self.assertJobsEqual('all', ['fd'])
