''' Contains queries of the job DB. '''
from compmake.jobs.storage import get_computation, all_jobs
from compmake.jobs.uptodate import up_to_date


def direct_parents(job_id):
    ''' Returns the direct parents of the specified job.
        (Jobs that depend directly on this one) '''
    assert(isinstance(job_id, str))
    computation = get_computation(job_id)
    return [x.job_id for x in computation.needed_by]
    
def direct_children(job_id):
    ''' Returns the direct children (dependences) of the specified job '''
    assert(isinstance(job_id, str))
    computation = get_computation(job_id)
    return [x.job_id for x in computation.depends]

def top_targets():
    """ Returns a list of all jobs which are not needed by anybody """
    return [x for x in all_jobs() if not direct_parents(x)]
    
def bottom_targets():
    """ Returns a list of all jobs with no dependencies """
    return [x for x in all_jobs() if not direct_children(x)]

# TODO should this be children()
def tree(jobs):
    ''' Returns the tree of all dependencies of the jobs '''
    t = set(jobs)
    for job_id in jobs:
        children_id = direct_children(job_id)
        t = t.union(tree(children_id))
    return t

def parents(job_id):
    ''' Returns the set of all the parents, grandparents, etc. 
        (does not include job_id) '''
    assert(isinstance(job_id, str))
    t = set()
    for p in direct_parents(job_id):
        t.add(p)
        t.update(parents(p))
    return t
 

    
def list_todo_targets(jobs):
    """ returns set:
         todo:  set of job ids to do (children that are not up to date) """
    todo = set()
    for job_id in jobs:
        up, reason = up_to_date(job_id) #@UnusedVariable
        if not up:
            todo.add(job_id)
            children_id = direct_children(job_id)
            todo.update(list_todo_targets(children_id))
    return todo
