from nose.tools import istest

from .compmake_test import CompmakeTest


def recursive(context, v):
    if v == 0:
        print('finally!')
        return

    context.comp_dynamic(recursive, v - 1, job_id='r%d' % v)


@istest
class TestDynamic2(CompmakeTest):

    howmany = None  # used by cases()

    def test_dynamic1(self):
        recursive(self.cc, 5)
        for _ in range(5):
            self.assert_cmd_success('ls;make;ls')
        self.assertJobsEqual('all', ['r1', 'r2', 'r3', 'r4', 'r5'])
        self.assertJobsEqual('done', ['r1', 'r2', 'r3', 'r4', 'r5'])
