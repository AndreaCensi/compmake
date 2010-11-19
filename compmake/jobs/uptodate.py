''' Contains functions concerning the up-to-date status of jobs '''
from compmake.structures import Cache
from compmake.jobs.storage import get_job_cache
from compmake.jobs.queries import direct_children
    
# XXX not used for now
up_to_date_cache = set()

#def invalidate_uptodate_cache():
    
def up_to_date(job_id):
    """ Check that the job is up to date. 
    We are up to date if:
    *) we are in the up_to_date_cache
       (nothing uptodate can become not uptodate so this is generally safe)
    OR
    1) we have a cache AND the timestamp is not 0 (force remake) or -1 (temp)
    2) the children are up to date AND
    3) the children timestamp is older than this timestamp 
    
    Returns:
    
        boolean, explanation 
    
    """ 
    global up_to_date_cache
    if job_id in up_to_date_cache:
        return True, 'cached result'
    
    cache = get_job_cache(job_id) # OK
    
    if cache.state == Cache.NOT_STARTED:
        return False, 'Not started'
        
    for child in direct_children(job_id):
        child_up, why = up_to_date(child) #@UnusedVariable
        if not child_up:
            return False, 'Children not up to date.'
        else:
            this_timestamp = cache.timestamp
            child_timestamp = get_job_cache(child).timestamp
            if child_timestamp > this_timestamp:
                return False, 'Children have been updated.'
    
    # FIXME BUG if I start (in progress), children get updated,
    # I still finish the computation instead of starting again
    if cache.state == Cache.IN_PROGRESS:
        return False, 'Resuming progress'
    elif cache.state == Cache.FAILED:
        return False, 'Failed'
            
    assert(cache.state in [Cache.DONE, Cache.MORE_REQUESTED])

    # FIXME: the cache is broken for now
    # up_to_date_cache.add(job_id)
    
    return True, ''

def list_todo_targets(jobs):
    """ returns a tuple (todo, jobs_done):
         todo:  set of job ids to do (children that are not up to date) 
         done:  top level targets (in jobs) that are already done. 
    """
    todo = set()
    done = set()
    for job_id in jobs:
        up, reason = up_to_date(job_id) #@UnusedVariable
        if not up:
            todo.add(job_id)
            children_id = direct_children(job_id)
            todo.update(list_todo_targets(children_id)[0])
        else:
            done.add(job_id)
            
    return todo, done

def dependencies_up_to_date(job_id):
    ''' Returns true if all the dependencies are up to date '''
    for child in direct_children(job_id):
        child_up, reason = up_to_date(child) #@UnusedVariable
        if not child_up:
            return False
    return True
