from .compmake_test import CompmakeTest
from nose.tools import istest
from compmake.stats import compmake_execution_stats
from compmake.jobs.storage import get_job_userobject


def f(*args):  # @UnusedVariable
    return

@istest
class TestExecutionStats(CompmakeTest):

    def test_execution_stats(self):
        from compmake import comp, batch_command
        # schedule some commands
        res = comp(f, comp(f), comp(f, comp(f)))
        
        result = compmake_execution_stats(res)
        batch_command('make')
    
        res = get_job_userobject(result.job_id)
        
        assert isinstance(res, dict)
        res['cpu_time']
        res['wall_time']
        res['jobs']
        
        print res
        
