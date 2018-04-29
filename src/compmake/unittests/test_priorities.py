# -*- coding: utf-8 -*-
from nose.tools import istest

from .. import set_compmake_status, CompmakeConstants
from .compmake_test import CompmakeTest


def bottom():
    TestOrder.order.append('bottom')


def bottom2():
    TestOrder.order.append('bottom2')


def top(x):  # @UnusedVariable
    TestOrder.order.append('top')


@istest
class TestOrder(CompmakeTest):

    order = []

    def mySetUp(self):
        # TODO: use tmp dir
        set_compmake_status(CompmakeConstants.compmake_status_embedded)
        # clear the variable holding the result
        TestOrder.order = []

    def test_order(self):
        # add two copies
        self.comp(top, self.comp(bottom))
        self.comp(top, self.comp(bottom))

        self.cc.batch_command('clean')
        self.cc.batch_command('make')

        self.assertEqual(['bottom', 'top', 'bottom', 'top'], TestOrder.order)

    def test_order_2(self):
        # choose wisely here
        self.comp(top, self.comp(bottom))
        self.comp(top, self.comp(bottom))
        self.comp(bottom2)

        self.cc.batch_command('clean')
        self.cc.batch_command('make')

        self.assertEqual(['bottom2', 'bottom', 'top', 'bottom', 'top'],
                         TestOrder.order)

    def test_order_3(self):
        # choose wisely here
        self.comp(top, self.comp(bottom2))
        self.comp(bottom)
        self.comp(top, self.comp(bottom2))

        self.cc.batch_command('clean')
        self.cc.batch_command('make')

        self.assertEqual(['bottom', 'bottom2', 'top', 'bottom2', 'top'],
                         TestOrder.order)
