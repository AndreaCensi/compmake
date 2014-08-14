from compmake import Promise
from compmake.jobs import get_job_cache, tree
from compmake.structures import Cache
from contracts import contract

__all__ = ['compmake_execution_stats']


@contract(promise=Promise, returns=Promise)
def compmake_execution_stats(context, promise):
    """ 
        Returns a promise for a the execution stats of a job
        and its dependencies.
    """
    job_id = promise.job_id
    db = context.get_compmake_db()
    jobs = tree([job_id], db=db)
    
    caches = []
    for j in jobs:
        cache = context.comp_dynamic(my_get_job_cache, j, extra_dep=[Promise(j)])
        caches.append(cache)
        
    return context.comp(finalize_result, jobs, caches)

def my_get_job_cache(context, job_id):
    """ Gets the job cache, making sure it was done """
    db = context.get_compmake_db()
    cache = get_job_cache(job_id, db=db)
    if cache.state != Cache.DONE:
        msg = 'The job %s was supposed to be finished: %s' % (job_id, cache) 
        raise Exception(msg)
    return cache

# @contract(caches='list[>=1]')
def finalize_result(jobs, caches):
    import numpy as np
    
    @contract(cache=Cache)
    def stats_from_cache(cache):
        assert isinstance(cache, Cache)
        return dict(walltime=cache.walltime_used, cputime=cache.cputime_used)
        
    allstats = list(map(stats_from_cache, caches))
    
    cpu_time = sum(x['cputime'] for x in allstats)
    wall_time = sum(x['walltime'] for x in allstats)
    return dict(cpu_time=cpu_time, wall_time=wall_time, jobs=jobs)    
    

