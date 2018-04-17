# -*- coding: utf-8 -*-
from compmake.structures import Cache

__all__ = [
    'compute_priorities'
]


def compute_priorities(all_targets, cq, priorities=None):
    """ Computes the priority for all_targets.

        :param priorities: str->float: cache
    """
    if priorities is None:
        priorities = {}
    all_targets = set(all_targets)
    for job_id in all_targets:
        p = compute_priority(job_id=job_id, priorities=priorities,
                             targets=all_targets, cq=cq)
        priorities[job_id] = p
    return priorities


def compute_priority(job_id, priorities, targets, cq):
    """ Computes the priority for one job. It uses caching results in
        self.priorities if they are found. """
    if job_id in priorities:
        return priorities[job_id]

    parents = set(cq.direct_parents(job_id))
    parents_which_are_targets = [x for x in parents if x in targets]

    # Dynamic jobs get bonus 
    job = cq.get_job(job_id)
    if job.needs_context:
        base_priority = 10
    else:
        base_priority = -1

    if not parents:
        # top level target
        base_priority += 5

    cache = cq.get_job_cache(job_id)
    if cache.state == Cache.FAILED:
        base_priority -= 100

    if not parents_which_are_targets:
        priority = base_priority
    else:
        pf = lambda p: compute_priority(p, priorities, targets, cq=cq)
        # it was -1
        parents_priority = list(map(pf, parents_which_are_targets))
        # priority = base_priority + max(parents_priority)
        priority = base_priority + sum(parents_priority)

    priorities[job_id] = priority

    return priority



