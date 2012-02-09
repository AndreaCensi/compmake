import unittest
from abc import ABCMeta, abstractmethod
from tempfile import mkdtemp
from shutil import rmtree
from compmake.state import CompmakeGlobalState
from compmake.storage import use_filesystem


class CompmakeTest(unittest.TestCase):
    __metaclass__ = ABCMeta

    def setUp(self):
        print('------- init %s -------' % self)
        self.root = mkdtemp()
        use_filesystem(self.root)

        # make sure everything was clean
        db = CompmakeGlobalState.db
        for key in db.keys('*'):
            db.delete(key)

        self.mySetUp()

    @abstractmethod
    def mySetUp(self):
        pass

    def tearDown(self):
        rmtree(self.root)
