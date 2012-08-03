import unittest
from abc import ABCMeta
from tempfile import mkdtemp
from shutil import rmtree
from compmake.state import CompmakeGlobalState, get_compmake_db
from compmake.storage import use_filesystem
import functools
from .. import logger


def compmake_environment(f):
    @functools.wraps(f)
    def wrapper():
        root = mkdtemp()
        use_filesystem(root)
        CompmakeGlobalState.jobs_defined_in_this_session = set()
        # make sure everything was clean
        db = get_compmake_db()
        for key in db.keys():
            db.delete(key)
        try:
            f()
        except:
            s = 'Keys in DB:'
            for key in db.keys():
                s += ' %s\n' % key
            logger.error('DB state after test %s' % f)
            logger.error(s)
            raise
        finally:
            rmtree(root)
    return wrapper


class CompmakeTest(unittest.TestCase):
    __metaclass__ = ABCMeta

    def setUp(self):
        self.root = mkdtemp()
        use_filesystem(self.root)

        # make sure everything was clean
        db = get_compmake_db()
        for key in db.keys():
            db.delete(key)

        self.mySetUp()

    def mySetUp(self):
        pass

    def tearDown(self):
        rmtree(self.root)
