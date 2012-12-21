''' Contains functions concerning the up-to-date status of jobs '''
from . import direct_children, get_job_cache
from ..structures import Cache
from contracts import contract
  

def up_to_date_slow(job_id):
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

    # simple local result cache

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

    assert(cache.state == Cache.DONE)
 
    return True, ''

#UpToDate = namedtuple('UpToDate', 'up timestamp ')

@contract(returns='tuple(bool, str)')
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
    cq = CacheQueryDB()
    res, reason, _ = cq.up_to_date(job_id)
    return res, reason


class CacheQueryDB(object):
    
    def __init__(self):
        self.up_to_date_cache = {} # string -> (bool, reason, timestamp)
        self.get_job_cache_cache = {}
    
    @contract(returns=Cache)
    def get_job_cache(self, job_id):
        if not job_id in self.get_job_cache_cache:
            self.get_job_cache_cache[job_id] = get_job_cache(job_id)
        return self.get_job_cache_cache[job_id]
    
    @contract(returns='tuple(bool, str, float)')
    def up_to_date(self, job_id):
        if job_id in self.up_to_date_cache:
            return self.up_to_date_cache[job_id]
        res = self.up_to_date_actual(job_id)
        self.up_to_date_cache[job_id] = res
        return res
    
    @contract(returns='tuple(bool, str, float)')
    def up_to_date_actual(self, job_id):
            
        cache = get_job_cache(job_id) # OK
    
        if cache.state == Cache.NOT_STARTED:
            return False, 'Not started', cache.timestamp
    
        for child in direct_children(job_id):
            child_up, _, child_timestamp = self.up_to_date(child)
            if not child_up:
                return False, 'Children not up to date.', cache.timestamp
            else:
                if child_timestamp > cache.timestamp:
                    return False, 'Children have been updated.', cache.timestamp
    
        # FIXME BUG if I start (in progress), children get updated,
        # I still finish the computation instead of starting again
        if cache.state == Cache.IN_PROGRESS:
            return False, 'Resuming progress', cache.timestamp
        elif cache.state == Cache.FAILED:
            return False, 'Failed', cache.timestamp
    
        assert(cache.state == Cache.DONE)
     
        return True, '', cache.timestamp
#
#    def list_todo_targets(self, jobs):
#        """ returns a tuple (todo, jobs_done):
#             todo:  set of job ids to do (children that are not up to date) 
#             done:  top level targets (in jobs) that are already done. 
#        """
#        todo = set()
#        done = set()
#        
##        seen = set()
##        stack = list()
##        stack.extend(jobs)
#         
#        while stack:
#            job_id = stack.pop()
#            seen.add(job_id)
#            up, _, _ = self.up_to_date(job_id)
#            if up: 
#                done.add(job_id)
#            else:
#                todo.add(job_id)
#                
#                children = direct_children(job_id)
#                
#                for child in children:
#                    if not child in seen:
#                        stack.append(child)
#                
#        return todo, done



#def list_todo_targets_slow(jobs):
#    """ returns a tuple (todo, jobs_done):
#         todo:  set of job ids to do (children that are not up to date) 
#         done:  top level targets (in jobs) that are already done. 
#    """
#    todo = set()
#    done = set()
#     
#    for job_id in jobs:
#        up, _ = up_to_date(job_id)
#        if up: 
#            done.add(job_id)
#        else:
#            todo.add(job_id)
#            
#            children = direct_children(job_id)
#            todo.update(list_todo_targets(children)[0])
#
#    return todo, done

def list_todo_targets(jobs):
    """ returns a tuple (todo, jobs_done):
         todo:  set of job ids to do (children that are not up to date) 
         done:  top level targets (in jobs) that are already done. 
    """
    todo = set()
    done = set()
    
    seen = set()
    stack = list()
    stack.extend(jobs)
     
    while stack:
        job_id = stack.pop()
        seen.add(job_id)
        up, _ = up_to_date(job_id)
        if up: 
            done.add(job_id)
        else:
            todo.add(job_id)
            children = direct_children(job_id)
            
            for child in children:
                if not child in seen:
                    stack.append(child)
            
    return todo, done


def dependencies_up_to_date(job_id):
    ''' Returns true if all the dependencies are up to date '''
    for child in direct_children(job_id):
        child_up, reason = up_to_date(child) #@UnusedVariable
        if not child_up:
            return False
    return True
