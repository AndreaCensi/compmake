from abc import ABCMeta
from shutil import rmtree
from tempfile import mkdtemp
import unittest

from compmake.storage.filesystem import StorageFilesystem
from compmake.context import Context
from compmake.jobs.syntax.parsing import eval_alias, parse_job_list
from contracts import contract
#
#
# def compmake_environment(f):
#     @functools.wraps(f)
#     def wrapper():
#         root = mkdtemp()
#         use_filesystem(root)
#         CompmakeGlobalState.jobs_defined_in_this_session = set()
#         # make sure everything was clean
#         db = get_compmake_db()
#         for key in db.keys():
#             db.delete(key)
#         try:
#             f()
#         except:
#             s = 'Keys in DB:'
#             for key in db.keys():
#                 s += ' %s\n' % key
#             logger.error('DB state after test %s' % f)
#             logger.error(s)
#             raise
#         finally:
#             rmtree(root)
#     return wrapper


class CompmakeTest(unittest.TestCase):
    __metaclass__ = ABCMeta

    def setUp(self):
        self.root = mkdtemp()
        self.db = StorageFilesystem(self.root)
        self.cc = Context(db=self.db)
        self.mySetUp()

    def tearDown(self):
        rmtree(self.root)

    # optional init
    def mySetUp(self):
        pass

    # useful
    def comp(self, *args, **kwargs):
        return self.cc.comp(*args, **kwargs)

    def get_jobs(self, expression):
        """ Returns the list of jobs corresponding to the given expression. """
        return list(parse_job_list(expression, context=self.cc))

    def assert_cmd_success(self, cmds):
        """ Executes the (list of) commands and checks it was succesful. """
        res = self.cc.interpret_commands_wrap(cmds)
        self.assertEqual(res, 0)

    # useful tests
    def assertEqualSet(self, a, b):
        self.assertEqual(set(a), set(b))

    @contract(expr=str)
    def assertJobsEqual(self, expr, jobs):
        js = 'not-valid-yet'
        try:
            js = self.get_jobs(expr)
            self.assertEqualSet(js, jobs)
        except:
            print('expr %r -> %s' % (expr, js))
            print('differs from %s' % jobs)
            raise



