''' Contains functions concerning the up-to-date status of jobs '''
from contracts import contract

from ..structures import Cache
from ..utils import memoize_simple


__all__ = ['CacheQueryDB']


@contract(returns='tuple(bool, str)')
def up_to_date(job_id, db):
    """ 
    
    Check that the job is up to date. 
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
    cq = CacheQueryDB(db)
    res, reason, _ = cq.up_to_date(job_id)
    return res, reason


class CacheQueryDB(object):
    
    def __init__(self, db):
        self.db = db
    
    @memoize_simple
    @contract(returns=Cache)
    def get_job_cache(self, job_id):
        from compmake.jobs.storage import get_job_cache
        return get_job_cache(job_id, db=self.db)

    @memoize_simple
    @contract(returns='tuple(bool, str, float)')
    def up_to_date(self, job_id):
        return self._up_to_date_actual(job_id)

    
    @contract(returns='tuple(bool, str, float)')
    def _up_to_date_actual(self, job_id):
        cache = self.get_job_cache(job_id)  # OK
    
        if cache.state == Cache.NOT_STARTED:
            return False, 'Not started', cache.timestamp
    
        for child in self.direct_children(job_id):
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
    
    @memoize_simple
    def direct_children(self, job_id):
        from compmake.jobs.queries import direct_children
        return direct_children(job_id, db=self.db)

    @memoize_simple
    def dependencies_up_to_date(self, job_id):
        ''' Returns true if all the dependencies are up to date '''
        for child in self.direct_children(job_id):
            child_up, _, _ = self.up_to_date(child)  
            if not child_up:
                return False
        return True
    
    def list_todo_targets(self, jobs):
        
    
        """ returns a tuple (todo, jobs_done):
             todo:  set of job ids to do (children that are not up to date) 
             done:  top level targets (in jobs) that are already done. 
             ready: ready to do (dependencies_up_to_date)
        """
        todo = set()
        done = set() 
        seen = set()
        stack = list()
        stack.extend(jobs)
         
        class A:
            count = 0
        
        def summary():
            A.count += 1
            if A.count % 100 != 0:
                return  
        
            # print('seen: %5d stack: %5d => todo: %5d  done: %5d' % (len(seen), len(stack), len(todo), len(done)))
        
        while stack:
            summary()
            
            job_id = stack.pop()
            seen.add(job_id)
            res = self.up_to_date(job_id)
            
            up, _, _ = res
            if up: 
                done.add(job_id)
            else:
                todo.add(job_id)
                for child in self.direct_children(job_id):
                    if not child in seen:
                        stack.append(child)
                
        todo_and_ready = set([job_id for job_id in todo
                              if self.dependencies_up_to_date(job_id)])
    
        return todo, done, todo_and_ready
