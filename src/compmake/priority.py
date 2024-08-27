import math
import os
from dataclasses import dataclass
from typing import Any, Collection, Optional, cast

from zuper_commons.fs import safe_pickle_load
from zuper_commons.types import ZAssertionError
from . import logger
from .cachequerydb import CacheQueryDB
from .structures import Cache, Job, PersistentStats
from .types import CMJobID

_logger = logger
__all__ = [
    "compute_priorities",
]


def compute_priorities(
    all_targets: Collection[CMJobID], cq: CacheQueryDB, priorities: Optional[dict[CMJobID, float]] = None
) -> dict[CMJobID, float]:
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


MAX_PRIORITY = 1000.0

PSTATS_FILE = "pstats.pickle"
pstats: Optional[PersistentStats]
if os.path.exists(PSTATS_FILE):
    pstats = cast(PersistentStats, safe_pickle_load(PSTATS_FILE))
    # n = len(pstats.by_command)
    # logger.info(f'Loaded pstats with {n} entries')
else:
    pstats = None


def compute_priority(job_id: CMJobID, priorities: dict[CMJobID, float], targets: Collection[CMJobID], cq: CacheQueryDB) -> float:
    res, how = compute_priority_(job_id=job_id, priorities=priorities, targets=targets, cq=cq)

    if math.isnan(res):
        logger.error(f"Got NaN for {job_id} {how}")
        res = 0.0

    # if how != ['cached']:
    #     logger.info(f'Priority {res:5.2f} {job_id} {" ".join(how)}')
    return res


@dataclass
class StatsForPriority:
    prob_success: float
    prob_oom: float
    prob_timedout: float
    compute_time_percentile: float

    # check that none of these are Nan
    def __post_init__(self):
        for k, v in self.__dict__.items():
            if math.isnan(v):
                raise ZAssertionError(f"Got Nan for {k}", me=self)


def estimate_stats(job_id: CMJobID, job: Job, cache: Cache) -> StatsForPriority:
    SMALL_NONZERO = 0.01
    if cache.state == Cache.FAILED:
        if cache.is_timed_out():
            prob_success = SMALL_NONZERO
            prob_oom = SMALL_NONZERO
            prob_timedout = 1.0
            compute_time_percentile = 100.0
            # return base_priority, circumstances
        elif cache.is_oom():
            prob_success = SMALL_NONZERO
            prob_oom = 1.0
            prob_timedout = SMALL_NONZERO
            compute_time_percentile = 100.0
            # return base_priority, circumstances
        elif cache.is_skipped_test():
            prob_success = SMALL_NONZERO
            prob_oom = SMALL_NONZERO
            compute_time_percentile = 50.0
            prob_timedout = SMALL_NONZERO
            # return base_priority, circumstances
        else:
            prob_success = SMALL_NONZERO
            prob_oom = SMALL_NONZERO
            compute_time_percentile = 50.0
            prob_timedout = SMALL_NONZERO
    elif pstats and job_id in pstats.by_job:

        pstats_one = pstats.by_job[job_id]
        prob_success = pstats_one.prob_success
        prob_oom = pstats_one.prob_oom
        prob_timedout = pstats_one.prob_timedout

        compute_time_percentile = pstats_one.compute_time_percentile

    elif pstats and job.command_desc in pstats.by_command:

        pstats_one = pstats.by_command[job.command_desc]
        prob_success = pstats_one.prob_success
        compute_time_percentile = pstats_one.compute_time_percentile
        prob_oom = pstats_one.prob_oom
        prob_timedout = pstats_one.prob_timedout

    else:
        prob_success = 0.95
        prob_oom = SMALL_NONZERO
        compute_time_percentile = 50.0
        prob_timedout = SMALL_NONZERO

    return StatsForPriority(
        prob_success=prob_success, compute_time_percentile=compute_time_percentile, prob_oom=prob_oom, prob_timedout=prob_timedout
    )


DYNAMIC_PRIORITY = 100.0
REGULAR_PRIORITY = 10.0


def compute_priority_(
    job_id: CMJobID, priorities: dict[CMJobID, float], targets: Collection[CMJobID], cq: CacheQueryDB
) -> tuple[float, Any]:
    """Computes the priority for one job. It uses caching results in
    self.priorities if they are found."""

    circumstances = []
    if job_id in priorities:
        return priorities[job_id], ["cached"]

    # Dynamic jobs are the most important
    job = cq.get_job(job_id)
    if job.needs_context:
        nlevel = len(job.defined_by)
        circumstances.append("dynamic")
        base_priority = DYNAMIC_PRIORITY - nlevel
        return base_priority, circumstances

    parents = set(cq.direct_parents(job_id))
    parents_which_are_targets = [x for x in parents if x in targets]

    cache = cq.get_job_cache(job_id)

    sfp = estimate_stats(job_id, job, cache)

    # do not redo failed jobs
    if cache.state == Cache.FAILED:
        if cache.is_timed_out():
            circumstances.append("timed-out")
            base_priority = 0.0
            # return base_priority, circumstances
        elif cache.is_oom():
            circumstances.append("oom")
            base_priority = 0.0
            # return base_priority, circumstances
        elif cache.is_skipped_test():
            circumstances.append("skippedtest")
            base_priority = 0.0
            # return base_priority, circumstances
        else:
            circumstances.append("exception")
            base_priority = 0.1
    elif cache.state == Cache.PROCESSING:
        circumstances.append("processing")
        base_priority = 0.025
    else:
        base_priority = REGULAR_PRIORITY

        # base_priority = 10
    # else:
    #     base_priority = -1.0

    if not parents:
        parent_bonus = 0.0
        circumstances.append("no-parents")
        # base_priority += 5.0

    elif not parents_which_are_targets:
        circumstances.append("no-parents-targets")
        # priority = base_priority
        parent_bonus = 0.0
    else:
        circumstances.append("inherit-parents-priority")
        pf = lambda p: compute_priority(p, priorities, targets, cq=cq)
        # it was -1
        parents_priority = list(map(pf, parents_which_are_targets))
        max_p = max(parents_priority)

        parent_bonus = max_p
        # priority = max(base_priority, max(parents_priority) / 1.1)
        # priority = base_priority + sum(parents_priority)

    bonus_time = (100.0 - sfp.compute_time_percentile) / 100.0
    priority = base_priority * (1.0 + sfp.prob_success) * (1 + bonus_time) + parent_bonus
    #
    # if pstats is not None:
    #     if job.command_desc in pstats.by_command:
    #
    #         pstats_one = pstats.by_command[job.command_desc]
    #
    #         bonus = ((100.0 - pstats_one.compute_time_percentile) / 100.0) * 0.4
    #         priority *= bonus * pstats_one.prob_success
    #         circumstances.append(f'stats-mult-bonus={bonus}')
    #         # logger.info('Bonus %s %s %s' % (job.command_desc, bonus, priority))
    #     else:
    #         circumstances.append('no-stats')
    #         # msg = f'No stats for {job.command_desc}'
    #         # logger.info(msg)

    # priority = min(MAX_PRIORITY, priority)
    priorities[job_id] = priority

    return priority, circumstances
