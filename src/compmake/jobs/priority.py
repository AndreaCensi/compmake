from .queries import direct_parents


__all__ = ['compute_priorities', 'compute_priority']


def compute_priorities(all_targets, db):
    ''' Computes the priority for all_targets. '''
    all_targets = set(all_targets)
    priorities = {}
    for job_id in all_targets:
        priorities[job_id] = compute_priority(job_id, priorities, all_targets, db=db)
    return priorities


def compute_priority(job_id, priorities, targets, db):
    ''' Computes the priority for one job. It uses caching results in
        self.priorities if they are found. '''
    if job_id in priorities:
        return priorities[job_id]

    parents = set(direct_parents(job_id, db=db))
    parents_which_are_targets = [x for x in parents if x in targets]

    if not parents_which_are_targets:
        priority = 0
    else:
        priority = -1 + max(map(lambda p: compute_priority(p, priorities,
                                                           targets, db=db),
                         parents_which_are_targets))

    priorities[job_id] = priority

    return priority



