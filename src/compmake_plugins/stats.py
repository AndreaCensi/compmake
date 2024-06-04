""" The actual interface of some commands in commands.py """

from collections import defaultdict
from dataclasses import dataclass
from typing import Collection, Literal

from compmake import (
    CMJobID,
    Cache,
    CacheQueryDB,
    CompmakeConstants,
    Context,
    StateCode,
    VISUALIZATION,
    compmake_colored,
    get_job,
    get_job_cache,
    parse_job_list,
    ui_command,
)
from compmake.constants import CANCEL_REASON_OOM, CANCEL_REASON_TIMEOUT
from compmake_utils import pad_to_screen
from zuper_commons.ui import duration_compact
from zuper_utils_asyncio import SyncTaskInterface


@ui_command(section=VISUALIZATION)
async def stats(sti: SyncTaskInterface, args: list[str], context: Context, cq: CacheQueryDB) -> None:
    """Displays a coarse summary of the jobs state."""
    if not args:
        job_list = cq.all_jobs()
    else:
        job_list = parse_job_list(args, context=context, cq=cq)

    job_list = list(job_list)
    CompmakeConstants.aliases["last"] = job_list
    await display_stats(job_list, context)


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


async def display_stats(job_list: Collection[CMJobID], context: Context) -> None:
    db = context.get_compmake_db()
    states_order = [
        Cache.NOT_STARTED,
        Cache.PROCESSING,
        Cache.FAILED,
        Cache.BLOCKED,
        Cache.DONE,
        CANCEL_REASON_OOM,
        CANCEL_REASON_TIMEOUT,
        "exception",
    ]

    # initialize counters to 0
    states2count = dict(list(map(lambda x: (x, 0), states_order)))

    Outcomes = StateCode | Literal["all", "oom", "timedout", "exception"]

    def empty_dict():
        return dict(list(map(lambda x: (x, Stats()), states_order)) + [("all", Stats())])

    function2state2count: dict[str, dict[Outcomes, Stats]] = defaultdict(empty_dict)
    function2count: dict[str, Stats] = defaultdict(Stats)
    total = 0

    for job_id in job_list:
        cache = get_job_cache(job_id, db=db)
        states2count[cache.state] += 1
        total += 1

        function_id = get_job(job_id, db=db).command_desc
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
            else:
                fsall["exception"].update(cache)
                fss["exception"].update(cache)
        if total == 100:  # XXX: use standard method
            print("Loading a large number of jobs...\r")

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
        (Cache.DONE, "OK"),
        (Cache.FAILED, "F"),
        ("exception", "ex"),
        ("oom", "OOM"),
        ("timedout", "TO"),
        (Cache.BLOCKED, "block"),
        (Cache.PROCESSING, "processing"),
        (Cache.NOT_STARTED, "todo"),
    ]

    totals = defaultdict(lambda: 0)

    def sorting_key(x: str):
        return function2count[x].total_wall

    ordered = sorted(function2count, key=sorting_key)

    for function_id in ordered:
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
        cpu = duration_compact(t.total_cpu)
        wall = duration_compact(t.total_wall)
        overhead = duration_compact(t.overhead)
        print(f"    {function_id_pad}: {s}  w {wall:8} c {cpu:8} ov {overhead:8}")
    #
    # final = []
    # for state, desc in states:
    #     s = f"{totals[state]:7d} {desc}"
    #     if totals[state] > 0:
    #         s = compmake_colored(s, **Cache.state2color.get(state, {}))
    #     final.append(s)
    # final = " ".join(final)
    # print(f"    {'total'.rjust(flen)}: {final}.")
