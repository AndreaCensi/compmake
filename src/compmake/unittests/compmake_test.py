import unittest
from abc import ABCMeta
from tempfile import mkdtemp
from shutil import rmtree
from compmake.state import CompmakeGlobalState
from compmake.storage import use_filesystem
import functools


def compmake_environment(f):
    @functools.wraps(f)
    def wrapper():
        root = mkdtemp()
        use_filesystem(root)
        CompmakeGlobalState.jobs_defined_in_this_session = set()
        # make sure everything was clean
        db = CompmakeGlobalState.db
        for key in db.keys('*'):
            db.delete(key)

        try:
            f()
        finally:
            rmtree(root)
    return wrapper


class CompmakeTest(unittest.TestCase):
    __metaclass__ = ABCMeta

    def setUp(self):
        self.root = mkdtemp()
        use_filesystem(self.root)

        # make sure everything was clean
        db = CompmakeGlobalState.db
        for key in db.keys('*'):
            db.delete(key)

        self.mySetUp()

    def mySetUp(self):
        pass

    def tearDown(self):
        rmtree(self.root)
