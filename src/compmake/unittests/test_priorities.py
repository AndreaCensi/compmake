from .. import set_compmake_status, CompmakeConstants
from . import CompmakeTest
from nose.tools import istest


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
        from compmake import comp, batch_command
        # add two copies
        comp(top, comp(bottom))
        comp(top, comp(bottom))

        batch_command('clean')
        batch_command('make')

        self.assertEqual(['bottom', 'top', 'bottom', 'top'], TestOrder.order)

    def test_order_2(self):
        from compmake import comp, batch_command
        # choose wisely here
        comp(top, comp(bottom))
        comp(top, comp(bottom))
        comp(bottom2)

        batch_command('clean')
        batch_command('make')

        self.assertEqual(['bottom2', 'bottom', 'top', 'bottom', 'top'],
                         TestOrder.order)

    def test_order_3(self):
        from compmake import comp, batch_command
        # choose wisely here
        comp(top, comp(bottom2))
        comp(bottom)
        comp(top, comp(bottom2))

        batch_command('clean')
        batch_command('make')

        self.assertEqual(['bottom', 'bottom2', 'top', 'bottom2', 'top'],
                         TestOrder.order)
