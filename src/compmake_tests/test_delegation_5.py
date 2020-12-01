import unittest
from tempfile import mkdtemp

from nose.tools import istest

from compmake.context import Context
from compmake.jobs import CMJobID, get_job
from compmake.storage.filesystem import StorageFilesystem


def g():
    return 2


def f(context):
    return context.comp(g)


def e(context):
    return context.comp_dynamic(f)


def h(i):
    assert i == 2


def define_jobs(root):
    db = StorageFilesystem(root, compress=True)
    cc = Context(db=db)
    cc.comp(h, cc.comp_dynamic(e))
    return db, cc


@istest
class TestDelegation5(unittest.TestCase):
    """
        Here's the problem: when the master are overwritten then
        the additional dependencies are lost.
    """

    def test_delegation_5(self):
        root = mkdtemp()
        db, cc = define_jobs(root)
        job0 = get_job(CMJobID("h"), db)
        self.assertEqual(job0.children, {"e"})

        cc.batch_command("make;ls")

        job = get_job(CMJobID("h"), db)
        self.assertEqual(job.children, {"e", "e-f", "e-f-g"})
        print("parents: %s" % job.parents)
        print("children: %s" % job.children)

        cc.batch_command("ls")
        cc.batch_command("check_consistency raise_if_error=1")
        # Now just define h again
        db, cc = define_jobs(root)
        cc.batch_command("check_consistency raise_if_error=1")
        job2 = get_job(CMJobID("h"), db)
        self.assertEqual(job2.children, {"e", "e-f", "e-f-g"})
