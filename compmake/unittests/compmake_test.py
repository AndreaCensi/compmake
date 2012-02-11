import unittest
from abc import ABCMeta
from tempfile import mkdtemp
from shutil import rmtree
from compmake.state import CompmakeGlobalState
from compmake.storage import use_filesystem


def compmake_environment(f):
    def wrapper_test():
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

    return wrapper_test


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

#    @abstractmethod
    def mySetUp(self):
        pass

    def tearDown(self):
        rmtree(self.root)
