""" The actual interface of some commands in commands.py """

from collections import defaultdict
from dataclasses import dataclass
from typing import Collection, Literal

import numpy as np

from compmake import (
    CMJobID,
    Cache,
    CacheQueryDB,
    CompmakeConstants,
    Context,
    StateCode,
    VISUALIZATION,
    compmake_colored,
    ui_command,
)
from compmake.constants import CANCEL_REASON_OOM, CANCEL_REASON_TIMEOUT
from compmake.priority import PSTATS_FILE
from compmake.structures import PersistentStats, PersistentStatsOne
from compmake_utils import pad_to_screen
from zuper_commons.fs import safe_pickle_dump
from zuper_commons.ui import duration_compact
from zuper_utils_asyncio import SyncTaskInterface
from . import logger

_logger = logger


@ui_command(section=VISUALIZATION)
async def stats(
    sti: SyncTaskInterface, job_list: Collection[CMJobID], context: Context, cq: CacheQueryDB, write: bool = False
) -> None:
    """Displays a coarse summary of the jobs state."""
    _ = sti
    if not job_list:
        job_list = cq.all_jobs()
    # else:
    #     job_list = parse_job_list(args, context=context, cq=cq)

    job_list = list(job_list)
    CompmakeConstants.aliases["last"] = job_list
    await display_stats(job_list, context, write=write)


@dataclass
class Stats:
    njobs: int = 0

    njobs_completed: int = 0
    total_cpu: float = 0.0
    total_wall: float = 0.0
    overhead: float = 0.0

    def update(self, cache: Cache) -> None:
        self.njobs += 1
        if cache.state == Cache.DONE:
            self.njobs_completed += 1
            self.total_cpu += cache.cputime_used
            self.total_wall += cache.walltime_used
            self.overhead += cache.get_overhead()


async def display_stats(job_list: Collection[CMJobID], context: Context, write: bool) -> None:
    db0 = context.get_compmake_db()
    cq = CacheQueryDB(db0)
    states_order = [
        Cache.NOT_STARTED,
        Cache.PROCESSING,
        Cache.FAILED,
        Cache.BLOCKED,
        Cache.DONE,
        "skipped",
        "skipped-exception",
        CANCEL_REASON_OOM,
        CANCEL_REASON_TIMEOUT,
        "exception",
    ]

    # initialize counters to 0
    states2count = dict(list(map(lambda x: (x, 0), states_order)))

    Outcomes = StateCode | Literal["all", "oom", "timedout", "exception", "skipped", "skipped-exception"]

    def empty_dict():
        return dict(list(map(lambda x: (x, Stats()), states_order)) + [("all", Stats())])

    function2state2count: dict[str, dict[Outcomes, Stats]] = defaultdict(empty_dict)
    function2count: dict[str, Stats] = defaultdict(Stats)
    total = 0

    pstats = PersistentStats(by_command={}, by_job={})

    all_times = []

    for job_id in job_list:
        cache = cq.get_job_cache(job_id)

        if cache.cputime_used is not None:
            all_times.append(cache.cputime_used)
    all_times = np.array(all_times)

    for job_id in job_list:
        cache = cq.get_job_cache(job_id)
        states2count[cache.state] += 1
        total += 1
        job = cq.get_job(job_id)
        function_id = job.command_desc
        # initialize record if not present
        # if not function_id in function2state2count:
        #     function2state2count[function_id] = dict(list(map(lambda x: (x, Stats()), states_order)) + [("all", Stats())])
        # update
        fss = function2state2count[function_id]
        fss[cache.state].update(cache)

        function2count[function_id].update(cache)
        fsall = function2state2count["all"]
        fsall[cache.state].update(cache)
        function2count["all"].update(cache)
        # function2count['all'].update(cache)
        if cache.state == Cache.FAILED:
            if cache.is_oom():
                fsall[CANCEL_REASON_OOM].update(cache)
                fss[CANCEL_REASON_OOM].update(cache)
            elif cache.is_timed_out():
                fsall[CANCEL_REASON_TIMEOUT].update(cache)
                fss[CANCEL_REASON_TIMEOUT].update(cache)
            elif cache.is_skipped_test():
                fsall["skipped-exception"].update(cache)
                fss["skipped-exception"].update(cache)
            else:
                fsall["exception"].update(cache)
                fss["exception"].update(cache)

        if "Skipped" in (cache.result_type_qual or ""):
            fsall["skipped"].update(cache)
            fss["skipped"].update(cache)
        if total == 100:  # XXX: use standard method
            print("Loading a large number of jobs...\r")

        if cache.state in (Cache.FAILED, Cache.DONE):
            if cache.cputime_used is not None:
                if not len(all_times):
                    cp = 50.0
                else:
                    cp = my_percentile(cache.cputime_used, all_times)
            else:
                cp = 50.0
            pstats.by_job[job_id] = PersistentStatsOne(
                prob_success=1 if cache.state == Cache.DONE else 0,
                prob_failure=1 if cache.state == Cache.FAILED else 0,
                prob_timedout=1 if cache.is_timed_out() else 0,
                prob_oom=1 if cache.is_oom() else 0,
                average_compute_time=cache.cputime_used or 0,
                compute_time_percentile=cp,
            )

    if total == 0:
        print(pad_to_screen("No jobs found."))
        return

        # print("Found %s jobs in total." % total)
    #
    #     for state in states_order:
    #         desc = "%30s" % Cache.state2desc[state]
    #         # colorize output
    #         desc = compmake_colored(desc, **state2color[state])
    #
    #         num = states2count[state]
    #         if num > 0:
    #             print("%s: %5d" % (desc, num))

    print("Summary by function name:")

    flen = max((len(x) + len("()")) for x in function2state2count)
    flen = max(flen, len("total"))
    states = [
        (Cache.DONE, "✓"),
        ("skipped", "SK"),
        (Cache.FAILED, "𐄂"),
        ("exception", "!"),
        ("oom", "OOM"),
        ("timedout", "⏲"),
        ("skipped-exception", "SK!"),
        (Cache.BLOCKED, "⚠"),
        (Cache.PROCESSING, "⛭"),
        (Cache.NOT_STARTED, "🗉"),
    ]

    totals = defaultdict(lambda: 0)

    def sorting_key(x: str):
        return function2count[x].total_wall

    ordered = sorted(function2count, key=sorting_key)

    for i, function_id in enumerate(ordered):
        function_stats = function2state2count[function_id]
        alls = []
        for state, desc in states:
            st = function_stats[state]
            s = f"{st.njobs:7d} {desc}"
            if st.njobs > 0:
                s = compmake_colored(s, **Cache.state2color.get(state, {}))
            else:
                s = " " * len(s)
            alls.append(s)
            totals[state] += st.njobs
        s = " ".join(alls)
        function_id_pad = (function_id + "()").ljust(flen)

        t = function2count[function_id]
        speed_score = t.total_cpu / (1 + t.njobs_completed)
        cpu = duration_compact(t.total_cpu)
        wall = duration_compact(t.total_wall)
        overhead = duration_compact(t.overhead)
        speed_scores = duration_compact(speed_score)
        speed_scores = f"{speed_score:5.2f}"

        if not len(all_times):
            compute_time_percentile = 50.0
        else:
            compute_time_percentile = my_percentile(speed_score, all_times)

        pstats.by_command[function_id] = PersistentStatsOne(
            prob_success=function_stats[Cache.DONE].njobs / t.njobs,
            prob_failure=function_stats[Cache.FAILED].njobs / t.njobs,
            prob_oom=function_stats[CANCEL_REASON_OOM].njobs / t.njobs,
            prob_timedout=function_stats[CANCEL_REASON_TIMEOUT].njobs / t.njobs,
            average_compute_time=speed_score,
            compute_time_percentile=compute_time_percentile,
        )

        print(
            f"    {function_id_pad}:  {s}  each {speed_scores:8} {compute_time_percentile:5.1f}| w {wall:8} c {cpu:8} ov "
            f"{overhead:8}"
        )

    if write:
        safe_pickle_dump(pstats, PSTATS_FILE)
    # logger.info(pstats=pstats)
    #
    # final = []
    # for state, desc in states:
    #     s = f"{totals[state]:7d} {desc}"
    #     if totals[state] > 0:
    #         s = compmake_colored(s, **Cache.state2color.get(state, {}))
    #     final.append(s)
    # final = " ".join(final)
    # print(f"    {'total'.rjust(flen)}: {final}.")


def my_percentile(speed_score: float, all_times: np.array) -> float:
    nlower = np.sum(all_times < speed_score)
    p = 100.0 * nlower / len(all_times)
    # nbigger = len([x for x in all_times if x > speed_score])
    # p = 100 * nbigger / len(all_times)
    return p


#
# def compute_all_percentiles(P):
#     P_sorted = np.sort(P)
#     n = len(P_sorted)
#     rank = np.arange(1, n + 1) * 1.0
#     percentiles = (rank / n) * 100
#
#     # Mapping back to the original array order
#     original_order_percentiles = {value: percentile for value, percentile in zip(P_sorted, percentiles)}
#     result_percentiles = [original_order_percentiles[value] for value in P]
#
#     return result_percentiles
