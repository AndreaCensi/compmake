from abc import ABCMeta
import os
from shutil import rmtree
from tempfile import mkdtemp
import unittest

from contracts import contract

from compmake.context import Context
from compmake.jobs import parse_job_list
from compmake.scripts.master import compmake_main
from compmake.storage import StorageFilesystem


class CompmakeTest(unittest.TestCase):
    __metaclass__ = ABCMeta

    def setUp(self):
        self.root0 = mkdtemp()
        self.root = os.path.join(self.root0, 'compmake')
        # print('CompmakeTest using db %s' % self.root)
        self.db = StorageFilesystem(self.root, compress=True)
        self.cc = Context(db=self.db)
        self.mySetUp()

    def tearDown(self):
        rmtree(self.root0)

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
        msg = 'Command %r failed.' % cmds
        res = self.cc.interpret_commands_wrap(cmds)
        self.assertEqual(res, 0, msg=msg)

    def assert_cmd_fail(self, cmds):
        """ Executes the (list of) commands and checks it was succesful. """
        msg = 'Command %r did not fail.' % cmds
        res = self.cc.interpret_commands_wrap(cmds)
        self.assertNotEqual(res, 0, msg=msg)

    @contract(cmd_string=str)
    def assert_cmd_success_script(self, cmd_string):
        """ This runs the "compmake_main" script which recreates the DB and context from disk. """
        ret = compmake_main([self.root, '--nosysexit', '-c', cmd_string])
        self.assertEqual(ret, 0)

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



