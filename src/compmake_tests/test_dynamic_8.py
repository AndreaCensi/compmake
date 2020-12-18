from typing import cast

from compmake import direct_uptodate_deps_inverse_closure
from compmake import definition_closure, jobs_defined
from compmake.types import CMJobID
from compmake import direct_uptodate_deps_inverse

from .compmake_test import CompmakeTest
from nose.tools import istest


def always():
    pass


def other():
    pass


def fd(context):
    context.comp(always)
    print("fd sees %s" % TestDynamic8.define_other)
    if TestDynamic8.define_other:
        context.comp(other)


def mockup8(context):
    context.comp_dynamic(fd)


@istest
class TestDynamic8(CompmakeTest):

    define_other = True

    def test_dynamic8_remake(self):
        #         """ Re-execution creates more jobs.  """
        mockup8(self.cc)
        # run it
        TestDynamic8.define_other = True
        self.assert_cmd_success("make recurse=1")
        # we have three jobs defined
        self.assertJobsEqual("all", ["fd", "fd-always", "fd-other"])
        # clean and remake fd
        TestDynamic8.define_other = False
        self.assert_cmd_success("remake fd")
        # now the "other" job should disappear
        self.assertJobsEqual("all", ["fd", "fd-always"])

    def test_dynamic8_clean(self):
        #         """ Re-execution creates more jobs.  """
        mockup8(self.cc)
        # run it
        TestDynamic8.define_other = True
        self.assert_cmd_success("make recurse=1")
        # we have three jobs defined
        self.assertJobsEqual("all", ["fd", "fd-always", "fd-other"])
        # clean and remake fd
        TestDynamic8.define_other = False
        j = cast(CMJobID, "fd")
        self.assertJobsEqual("done", ["fd", "fd-always", "fd-other"])
        self.assertEqualSet(jobs_defined(j, self.db), ["fd-always", "fd-other"])

        self.assertEqualSet(definition_closure([j], self.db), ["fd-always", "fd-other"])
        direct = direct_uptodate_deps_inverse(j, self.db)
        self.assertEqualSet(direct, ["fd-always", "fd-other"])
        direct_closure = direct_uptodate_deps_inverse_closure(j, self.db)
        self.assertEqualSet(direct_closure, ["fd-always", "fd-other"])

        self.assert_cmd_success("clean fd")
        # clean should get rid of the jobs
        self.assertJobsEqual("all", ["fd"])
        self.assert_cmd_success("make fd")
        # now the "other" job should disappear
        self.assertJobsEqual("all", ["fd", "fd-always"])

    def test_dynamic8_inverse(self):
        """ Re-execution creates fewer jobs. """
        mockup8(self.cc)
        # run it
        TestDynamic8.define_other = False
        self.assert_cmd_success("make recurse=1")
        # we have two jobs defined
        self.assertJobsEqual("all", ["fd", "fd-always"])
        # clean and remake fd
        TestDynamic8.define_other = True
        self.assert_cmd_success("remake fd")
        # now the "other" job should disappear
        self.assertJobsEqual("all", ["fd", "fd-always", "fd-other"])
        self.assertJobsEqual("done", ["fd", "fd-always"])
