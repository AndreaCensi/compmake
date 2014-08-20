from .compmake_test import CompmakeTest
from compmake import compmake_execution_stats
from compmake.jobs import get_job_userobject
from nose.tools import istest

def f(*args):  # @UnusedVariable
    return

@istest
class TestExecutionStats(CompmakeTest):

    def test_execution_stats(self):
        comp = self.comp

        # schedule some commands
        res = comp(f, comp(f), comp(f, comp(f)))
        
        result = compmake_execution_stats(self.cc, res)
        self.cc.batch_command('make')
    
        res = get_job_userobject(result.job_id, db=self.db)
        
        assert isinstance(res, dict)
        res['cpu_time']
        res['wall_time']
        res['jobs']
        
        print(res)
        
