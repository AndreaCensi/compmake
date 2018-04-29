# -*- coding: utf-8 -*-
from nose.tools import istest
from .compmake_test import CompmakeTest
from .mockup import mockup2_nofail


@istest
class PluginsTest(CompmakeTest):

    def mySetUp(self):
        mockup2_nofail(self.cc)

    def testDetails(self):
        jobs = self.get_jobs('all')
        for job_id in jobs:
            self.assert_cmd_success('details %s' % job_id)
        self.assert_cmd_success('details %s %s' % (jobs[0], jobs[1]))

    def testList(self):
        jobs = self.get_jobs('all')
        self.assert_cmd_success('ls')
        self.assert_cmd_success('ls %s' % jobs[0])

        # empty list
        #self.assert_cmd_success('ls block* and done')

    # def testCredits(self):
    #     self.assert_cmd_success('credits')

    def testCheckConsistency(self):
        self.assert_cmd_success('check-consistency')

    def testDump(self):
        dirname = self.cc.get_compmake_db().basepath
        jobs = self.get_jobs('done')
        for job_id in jobs:
            self.assert_cmd_success('dump directory=%s %s' % (dirname, job_id))

        # TODO: add check that it fails for not done
        jobs = self.get_jobs('not done')
        for job_id in jobs:
            self.assert_cmd_success('dump directory=%s %s' % (dirname, job_id))


