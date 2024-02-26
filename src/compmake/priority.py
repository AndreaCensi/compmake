from typing import Collection, Dict, Optional

from .cachequerydb import CacheQueryDB
from .structures import Cache
from .types import CMJobID

__all__ = [
    "compute_priorities",
]


def compute_priorities(
    all_targets: Collection[CMJobID], cq: CacheQueryDB, priorities: Optional[Dict[CMJobID, float]] = None
) -> Dict[CMJobID, float]:
    """Computes the priority for all_targets.

    priorities: str->float: cache
    """
    if priorities is None:
        priorities = {}
    all_targets = set(all_targets)
    for job_id in all_targets:
        p = compute_priority(job_id=job_id, priorities=priorities, targets=all_targets, cq=cq)
        # if job_id not in priorities:
        #     logger.debug(f'Priority {p} {job_id}')
        priorities[job_id] = p
    return priorities


MAX_PRIORITY = 1000


def compute_priority(job_id: CMJobID, priorities: Dict[CMJobID, float], targets: Collection[CMJobID], cq: CacheQueryDB) -> float:
    """Computes the priority for one job. It uses caching results in
    self.priorities if they are found."""
    if job_id in priorities:
        return priorities[job_id]

    parents = set(cq.direct_parents(job_id))
    parents_which_are_targets = [x for x in parents if x in targets]

    cache = cq.get_job_cache(job_id)
    # do not redo failed jobs
    if cache.state == Cache.FAILED:
        return 0.0

    # Dynamic jobs get bonus
    job = cq.get_job(job_id)
    if job.needs_context:
        base_priority = MAX_PRIORITY
        nlevel = len(job.defined_by)
        return base_priority - nlevel
        # base_priority = 10
    else:
        base_priority = -1.0

    if not parents:
        # top level target
        base_priority += 5.0

    if not parents_which_are_targets:
        priority = base_priority
    else:
        pf = lambda p: compute_priority(p, priorities, targets, cq=cq)
        # it was -1
        parents_priority = list(map(pf, parents_which_are_targets))
        priority = max(base_priority, max(parents_priority) / 2)
        # priority = base_priority + sum(parents_priority)

    priorities[job_id] = priority

    return priority
