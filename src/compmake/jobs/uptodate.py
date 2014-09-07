''' Contains functions concerning the up-to-date status of jobs '''
from ..structures import Cache, Job
from ..utils import memoized_reset
from contracts import contract
from compmake.structures import CompmakeBug
from compmake.jobs.dependencies import collect_dependencies
from compmake.jobs.storage import get_job_userobject
from contracts.utils import check_isinstance


__all__ = [
    'CacheQueryDB',
]


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
    """ 
        This works as a view on a DB which is assumed not to change
        between calls. 
    """
    
    def __init__(self, db):
        self.db = db
    
    def invalidate(self):
        self.get_job_cache.reset()
        self.get_job.reset()
        self.all_jobs.reset()
        self.job_exists.reset()
        self.up_to_date.reset()
        self.direct_children.reset()
        self.direct_parents.reset()
        self.dependencies_up_to_date.reset()
        
    @memoized_reset
    @contract(returns=Cache)
    def get_job_cache(self, job_id):
        from .storage import get_job_cache
        return get_job_cache(job_id, db=self.db)

    @memoized_reset
    @contract(returns=Job)
    def get_job(self, job_id):
        from .storage import get_job
        return get_job(job_id, db=self.db)

    @memoized_reset
    def all_jobs(self):
        from .storage import all_jobs
        # NOTE: very important, do not memoize iterator
        return list(all_jobs(db=self.db))

    @memoized_reset
    def job_exists(self, job_id):
        from .storage import job_exists
        return job_exists(job_id=job_id, db=self.db)

    @memoized_reset
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
    
    @memoized_reset
    def direct_children(self, job_id):
        from compmake.jobs.queries import direct_children
        return direct_children(job_id, db=self.db)

    @memoized_reset
    def direct_parents(self, job_id):
        from compmake.jobs.queries import direct_parents
        return direct_parents(job_id, db=self.db)

    @memoized_reset
    def dependencies_up_to_date(self, job_id):
        ''' Returns true if all the dependencies are up to date '''
        for child in self.direct_children(job_id):
            child_up, _, _ = self.up_to_date(child)  
            if not child_up:
                return False
        return True
    
    def tree(self, jobs):
        """ More efficient version of tree() 
            which is direct_children() recursively. """
        stack = []
        
        stack.extend(jobs)
        
        result = set()
        
        while stack:
            job_id = stack.pop()
            
            for c in self.direct_children(job_id):
                if not c in result:
                    result.add(c)
                    stack.append(c)
                    
        return list(result)
       
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
                    if not self.job_exists(child):
                        msg = 'Job %r references not existing %r' % (job_id, child)
                        raise CompmakeBug(msg)
                    if not child in seen:
                        stack.append(child)
                
        todo_and_ready = set([job_id for job_id in todo
                              if self.dependencies_up_to_date(job_id)])
    
        return todo, done, todo_and_ready


    @contract(returns=set, jobs='str|set(str)')
    def tree_children_and_uodeps(self, jobs):
        """ Closure of the relation children and dependencies of userobject. """
        stack = []
        if isinstance(jobs, str):
            jobs = [jobs]
        
        stack.extend(jobs)
        
        result = set()
        
        def descendants(job_id):
            deps = collect_dependencies(get_job_userobject(job_id, self.db))
            children = self.direct_children(job_id)
            check_isinstance(children, set)
            r = children | deps
            check_isinstance(r, set)
            return r
        
        while stack:
            job_id = stack.pop()    
            
            for c in descendants(job_id):
                if not self.job_exists(c):
                    raise ValueError(c)
                if not c in result:
                    result.add(c)
                    stack.append(c)
                    
        return result
    
    
    