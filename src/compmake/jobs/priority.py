from .queries import direct_parents
from compmake.jobs.storage import get_job


__all__ = [
    'compute_priorities', 
    'compute_priority',
]


def compute_priorities(all_targets, db):
    ''' Computes the priority for all_targets. '''
    all_targets = set(all_targets)
    priorities = {}
    for job_id in all_targets:
        p = compute_priority(job_id, priorities, all_targets, db=db)
        priorities[job_id] = p
    return priorities


def compute_priority(job_id, priorities, targets, db):
    ''' Computes the priority for one job. It uses caching results in
        self.priorities if they are found. '''
    if job_id in priorities:
        return priorities[job_id]

    parents = set(direct_parents(job_id, db=db))
    parents_which_are_targets = [x for x in parents if x in targets]

    # Dynamic jobs get bonus 
    job = get_job(job_id, db=db)
    if job.needs_context:
        base_priority = 10
    else:
        base_priority = 0

    if not parents_which_are_targets:
        priority = base_priority
    else:
        pf = lambda p: compute_priority(p, priorities, targets, db=db)
        # it was -1
        priority = base_priority + max(list(map(pf, parents_which_are_targets)))

    priorities[job_id] = priority

    return priority



