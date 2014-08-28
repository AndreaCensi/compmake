from .queries import direct_parents
from compmake.jobs.storage import get_job


__all__ = [
    'compute_priorities', 
    'compute_priority',
]


def compute_priorities(all_targets, db, cq, priorities=None):
    ''' Computes the priority for all_targets. '''
    if priorities is None:
        priorities = {}
    all_targets = set(all_targets)
    for job_id in all_targets:
        p = compute_priority(job_id=job_id, priorities=priorities, targets=all_targets, db=db, cq=cq)
        priorities[job_id] = p
    return priorities


def compute_priority(job_id, priorities, targets, db, cq):
    ''' Computes the priority for one job. It uses caching results in
        self.priorities if they are found. '''
    if job_id in priorities:
        return priorities[job_id]

    parents = set(cq.direct_parents(job_id))
    parents_which_are_targets = [x for x in parents if x in targets]

    # Dynamic jobs get bonus 
    job = cq.get_job(job_id)
    if job.needs_context:
        base_priority = 10
    else:
        base_priority = 0

    if not parents_which_are_targets:
        priority = base_priority
    else:
        pf = lambda p: compute_priority(p, priorities, targets, db=db, cq=cq)
        # it was -1
        priority = base_priority + max(list(map(pf, parents_which_are_targets)))

    priorities[job_id] = priority

    return priority



