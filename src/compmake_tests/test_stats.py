from nose.tools import istest

from .compmake_test import CompmakeTest
from compmake import compmake_execution_stats
from zuper_commons.types import check_isinstance
from compmake.jobs.dependencies import get_job_userobject_resolved
from ..structures import CMJobID


def ff(*args):
    return


def gg(context):
    return context.comp(ff)


def hh(context):
    return context.comp_dynamic(gg)


@istest
class TestExecutionStats(CompmakeTest):
    def test_execution_stats(self):
        # schedule some commands
        res = self.cc.comp_dynamic(gg)

        myjobid = CMJobID("myjobid")
        compmake_execution_stats(self.cc, res, use_job_id=myjobid)
        self.assert_cmd_success("make recurse=1")

        res = get_job_userobject_resolved(myjobid, db=self.db)
        check_result(res)

        _ = res["cpu_time"]
        _ = res["wall_time"]

        print(res)
        self.assertEqual(res["jobs"], {"gg-ff", "gg"})

    def test_execution_stats2(self):
        # schedule some commands
        res = self.cc.comp_dynamic(hh)

        myjobid = "myjobid"
        compmake_execution_stats(self.cc, res, use_job_id=myjobid)
        self.assert_cmd_success("make recurse=1")
        self.assert_cmd_success("ls")

        res = get_job_userobject_resolved(myjobid, db=self.db)
        check_result(res)

        print(res)

        self.assertEqual(res["jobs"], set(["hh-gg-ff", "hh-gg", "hh"]))


def check_result(res):
    check_isinstance(res, dict)
    _ = res["cpu_time"]
    _ = res["wall_time"]
    _ = res["jobs"]
