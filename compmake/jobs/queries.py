''' Contains queries of the job DB. '''
from compmake.jobs.storage import get_job, all_jobs



def direct_parents(job_id):
    ''' Returns the direct parents of the specified job.
        (Jobs that depend directly on this one) '''
    assert(isinstance(job_id, str))
    computation = get_job(job_id)
    return computation.parents
    
def direct_children(job_id):
    ''' Returns the direct children (dependences) of the specified job '''
    assert(isinstance(job_id, str))
    computation = get_job(job_id)
    return computation.children

# XXX: these are redundant
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
    
