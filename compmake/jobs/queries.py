''' Contains queries of the job DB. '''
from compmake.jobs.storage import get_computation, all_jobs
from compmake.jobs.uptodate import up_to_date

def top_targets():
    """ Returns a list of all jobs which are not needed by anybody """
    return [x for x in all_jobs() if not get_computation(x).needed_by]
    
def bottom_targets():
    """ Returns a list of all jobs with no dependencies """
    return [x for x in all_jobs() if not get_computation(x).depends]

# TODO should this be children()
def tree(jobs):
    ''' Returns the tree of all dependencies of the jobs '''
    t = set(jobs)
    for job_id in jobs:
        computation = get_computation(job_id)
        children_id = [x.job_id for x in computation.depends]
        t = t.union(tree(children_id))
    return t

def parents(job_id):
    ''' Returns the set of all the parents, grandparents, etc. (does not include job_id) '''
    t = set()
    computation = get_computation(job_id)
    
    for x in computation.needed_by:
        t = t.union(parents(x.job_id))
    
    return t
 

def list_todo_targets(jobs):
    """ returns set:
         todo:  set of job ids to do (children that are not up to date) """
    todo = set()
    for job_id in jobs:
        up, reason = up_to_date(job_id) #@UnusedVariable
        if not up:
            todo.add(job_id)
            computation = get_computation(job_id)
            children_id = [x.job_id for x in computation.depends]
            todo = todo.union(list_todo_targets(children_id))
    return set(todo)
