# -*- coding: utf-8 -*-
from compmake.unittests.compmake_test import CompmakeTest
from nose.tools import istest


def always():
    pass


def other():
    pass


def dep():
    return TestDynamic9.define_other


def fd(context, dep):
    context.comp(always)
    print('fd sees dep=%s' % dep)
    if dep:
        context.comp(other)


def mockup9(context):
    depres = context.comp(dep)
    context.comp_dynamic(fd, dep=depres)


@istest
class TestDynamic9(CompmakeTest):
    define_other = True

    def test_dynamic9(self):
        """ Re-execution creates more jobs.  """
        mockup9(self.cc)
        # run it
        TestDynamic9.define_other = True  # returned by dep
        self.assert_cmd_success('make recurse=1')
        # we have 4 jobs defined
        self.assertJobsEqual('all', ['fd', 'fd-always', 'fd-other', 'dep'])
        # clean and remake fd
        TestDynamic9.define_other = False  # returned by dep
        # clean dep
        self.assert_cmd_success('remake dep')

        # now all jobs are done
        self.assertJobsEqual('done', ['fd', 'fd-always', 'fd-other', 'dep'])
        # but fd is not up to date
        self.assert_job_uptodate('fd', False)

        self.assert_cmd_success('make echo=1')  # remaking
        # now the "other" job should disappear
        self.assertJobsEqual('all', ['fd', 'fd-always', 'dep'])
