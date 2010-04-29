''' contains functions concerning the up-to-date status of jobs '''
from compmake.structures import Cache
from compmake.jobs.storage import get_job_cache, get_computation

def dependencies_up_to_date(job_id):
    computation = get_computation(job_id)
    dependencies_up_to_date = True
    for child in computation.depends:
        child_up, reason = up_to_date(child.job_id) #@UnusedVariable
        if not child_up:
            return False
    return True


    
up_to_date_cache = set()
def up_to_date(job_id):
    """ Check that the job is up to date. 
    We are up to date if:
    *) we are in the up_to_date_cache
       (nothing uptodate can become not uptodate so this is generally safe)
    OR
    1) we have a cache AND the timestamp is not 0 (force remake) or -1 (temp)
    2) the children are up to date AND
    3) the children timestamp is older than this timestamp AND
    
    Returns:
    
        boolean, explanation 
    
    """ 
    global up_to_date_cache
    if job_id in up_to_date_cache:
        return True, 'cached result'
    
    
    cache = get_job_cache(job_id) # OK
    
    if cache.state == Cache.NOT_STARTED:
        return False, 'Not started'
        
    computation = get_computation(job_id)
    for child in computation.depends:
        child_up, why = up_to_date(child.job_id) #@UnusedVariable
        if not child_up:
            return False, 'Children not up to date.'
        else:
            this_timestamp = cache.timestamp
            child_timestamp = get_job_cache(child.job_id).timestamp
            if child_timestamp > this_timestamp:
                return False, 'Children have been updated.'
    
    # FIXME BUG if I start (in progress), children get updated,
    # I still finish the computation instead of starting again
    if cache.state == Cache.IN_PROGRESS:
        return False, 'Resuming progress'
    elif cache.state == Cache.FAILED:
        return False, 'Failed'
            
    assert(cache.state in [Cache.DONE, Cache.MORE_REQUESTED])

    up_to_date_cache.add(job_id)
    
    return True, ''
