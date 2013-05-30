from compmake import Promise
from compmake.jobs import get_job_cache, tree
from compmake.structures import Cache
from compmake.ui import comp
from contracts import contract

__all__ = ['compmake_execution_stats']

# class ExecutionStats(object):
#     """ Result of compmake_execution_stats """
#     
#     @contract(cpu_time='float', wall_time='float')
#     def __init__(self, cpu_time, wall_time):
#         self.cpu_time = cpu_time
#         self.wall_time = wall_time


@contract(promise=Promise, returns=Promise)
def compmake_execution_stats(promise):
    """ 
        Returns a promise for a the execution stats of a job
        and its dependencies.
    """
    job_id = promise.job_id
    jobs = tree([job_id])
    print jobs
    
    caches = []
    for j in jobs:
        cache = comp(my_get_job_cache, j, extra_dep=[Promise(j)])
        caches.append(cache)
        
    return comp(finalize_result, jobs, caches)

def my_get_job_cache(job_id):
    """ Gets the job cache, making sure it was done """
    cache = get_job_cache(job_id)
    if cache.state != Cache.DONE:
        msg = 'The job %s was supposed to be finished: %s' % (job_id, cache) 
        raise Exception(msg)
    return cache

@contract(caches='list[>=1]')
def finalize_result(jobs, caches):
    import numpy as np
    print caches
    
    @contract(cache=Cache)
    def stats_from_cache(cache):
        assert isinstance(cache, Cache)
        return  np.array((cache.walltime_used, cache.cputime_used),
                         dtype=[('walltime', 'float'), ('cputime', 'float')])
        
    allstats = map(stats_from_cache, caches)
    allstats = np.hstack(allstats)
    
    cpu_time = np.sum(allstats['cputime'])
    wall_time = np.sum(allstats['walltime'])
    return dict(cpu_time=cpu_time, wall_time=wall_time,
                jobs=jobs)    
    

