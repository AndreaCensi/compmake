from abc import ABCMeta
from compmake.context import Context
from compmake.jobs import get_job, parse_job_list
from compmake.scripts.master import compmake_main
from compmake.storage import StorageFilesystem
from compmake.structures import CommandFailed, Job, MakeFailed
from contracts import contract
from shutil import rmtree
from tempfile import mkdtemp
import os
import unittest


class CompmakeTest(unittest.TestCase):
    __metaclass__ = ABCMeta

    def setUp(self):
        self.root0 = mkdtemp()
        self.root = os.path.join(self.root0, 'compmake')
        self.db = StorageFilesystem(self.root, compress=True)
        self.cc = Context(db=self.db)
        self.mySetUp()

    def tearDown(self):
        if False:
            print('not deleting %s' % self.root0)
        else:
            rmtree(self.root0)

    # optional init
    def mySetUp(self):
        pass

    # useful
    def comp(self, *args, **kwargs):
        return self.cc.comp(*args, **kwargs)

    @contract(job_id=str, returns=Job)
    def get_job(self, job_id):
        db = self.cc.get_compmake_db()
        return get_job(job_id=job_id, db=db)

    def get_jobs(self, expression):
        """ Returns the list of jobs corresponding to the given expression. """
        return list(parse_job_list(expression, context=self.cc))

    def assert_cmd_success(self, cmds):
        """ Executes the (list of) commands and checks it was succesful. """
        try:
            print('@ %s' % cmds)
            self.cc.interpret_commands_wrap(cmds)
            
        except MakeFailed as e:
            print('Detected MakeFailed')
            print('Failed jobs: %s' % e.failed)
            for job_id in e.failed:
                self.cc.interpret_commands_wrap('details %s' % job_id)
            
        except CommandFailed:
            #msg = 'Command %r failed. (res=%s)' % (cmds, res)
            raise
        
        
        self.cc.interpret_commands_wrap('check_consistency raise_if_error=1')

        

    def assert_cmd_fail(self, cmds):
        """ Executes the (list of) commands and checks it was succesful. """
        
        try:
            self.cc.interpret_commands_wrap(cmds)
        except CommandFailed:
            pass
        else:
            msg = 'Command %r did not fail.' % cmds 
            raise Exception(msg)

    @contract(cmd_string=str)
    def assert_cmd_success_script(self, cmd_string):
        """ This runs the "compmake_main" script which recreates the DB and context from disk. """
        ret = compmake_main([self.root, '--nosysexit', '-c', cmd_string])
        self.assertEqual(ret, 0)

    # useful tests
    def assert_defined_by(self, job_id, expected):
        self.assertEqual(self.get_job(job_id).defined_by, expected)

    def assertEqualSet(self, a, b):
        self.assertEqual(set(a), set(b))

    @contract(expr=str)
    def assertJobsEqual(self, expr, jobs, ignore_dyn_reports=True):
        
        js = 'not-valid-yet'
        try:
            js = self.get_jobs(expr)
            if ignore_dyn_reports:
                js = [x  for x in js if not 'dynreports' in x]
            self.assertEqualSet(js, jobs)
        except:
            print('expr %r -> %s' % (expr, js))
            print('differs from %s' % jobs)
            raise

    def assertMakeFailed(self, func, nfailed, nblocked):
        try:
            func()
        except MakeFailed as e:
            if len(e.failed) != nfailed:
                msg = 'Expected %d failed, got %d: %s' % (nfailed, len(e.failed), e.failed) 
                raise Exception(msg)
            if len(e.blocked) != nblocked:
                msg = 'Expected %d blocked, got %d: %s' % (nblocked, len(e.blocked), e.blocked) 
                raise Exception(msg)
        except Exception as e:
            raise Exception('unexpected: %s' % e)
        
        
        
        
        