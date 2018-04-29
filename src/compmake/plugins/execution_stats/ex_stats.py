# -*- coding: utf-8 -*-
from compmake import Promise
from compmake.jobs import get_job_cache
from compmake.jobs.uptodate import CacheQueryDB
from compmake.structures import Cache
from contracts import check_isinstance, contract

__all__ = [
    'compmake_execution_stats',
]


@contract(promise='str|isinstance(Promise)', returns=Promise)
def compmake_execution_stats(context, promise, use_job_id=None):
    """ 
        Returns a promise for a the execution stats of a job
        and its dependencies.
    """
    check_isinstance(promise, (Promise, str))
    
    if isinstance(promise, Promise):
        job_id = promise.job_id
    elif isinstance(promise, str):
        job_id = promise    
        promise = Promise(job_id)
    else:
        assert False
        
    p2 = context.comp(dummy, promise)
    if use_job_id is not None:
        context.comp_prefix(None)
        return context.comp_dynamic(count_resources, the_job=job_id, job_id=use_job_id,
                                    extra_dep=p2)
    else:
        return context.comp_dynamic(count_resources, the_job=job_id,
                                    extra_dep=p2)


def dummy(*args):
    pass


def count_resources(context, the_job):
    db = context.get_compmake_db()
    cache = get_job_cache(the_job, db=db)
    if cache.state != Cache.DONE:
        msg = 'The job %s was supposed to be finished: %s' % (the_job, cache) 
        raise Exception(msg)
    
    cq = CacheQueryDB(db)
    children = cq.tree_children_and_uodeps(the_job)
    check_isinstance(children, set)
    children.add(the_job)
    
    res = {}
    for j in children:
        res[j] = context.comp_dynamic(my_get_job_cache, j, extra_dep=[Promise(j)],
                                     job_id='count-%s-%s' % (the_job, j))
        
    return context.comp(finalize_result, res)

def my_get_job_cache(context, the_job):
    """ Gets the job cache, making sure it was done """
    db = context.get_compmake_db()
    cache = get_job_cache(the_job, db=db)
    if cache.state != Cache.DONE:
        msg = 'The job %s was supposed to be finished: %s' % (the_job, cache) 
        raise Exception(msg)
    return cache

# @contract(caches='list[>=1]')
def finalize_result(res):
    @contract(cache=Cache)
    def stats_from_cache(cache):
        check_isinstance(cache, Cache)
        return dict(walltime=cache.walltime_used, cputime=cache.cputime_used)
        
    jobs = set(res.keys())
    allstats = list(map(stats_from_cache, res.values()))
    
    cpu_time = sum(x['cputime'] for x in allstats)
    wall_time = sum(x['walltime'] for x in allstats)
    return dict(cpu_time=cpu_time, wall_time=wall_time, jobs=jobs)    
    

