""" The actual interface of some commands in commands.py """

from collections import defaultdict
from typing import Collection

from compmake import (
    CMJobID,
    Cache,
    CacheQueryDB,
    CompmakeConstants,
    Context,
    VISUALIZATION,
    compmake_colored,
    get_job,
    get_job_cache,
    parse_job_list,
    ui_command,
)
from compmake_utils import pad_to_screen
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
    display_stats(job_list, context)


def display_stats(job_list: Collection[CMJobID], context: Context) -> None:
    db = context.get_compmake_db()
    states_order = [
        Cache.NOT_STARTED,
        Cache.PROCESSING,
        Cache.FAILED,
        Cache.BLOCKED,
        Cache.DONE,
    ]
    # initialize counters to 0
    states2count = dict(list(map(lambda x: (x, 0), states_order)))

    function2state2count: dict[str, dict[str, int]] = {}
    total = 0

    for job_id in job_list:
        cache = get_job_cache(job_id, db=db)
        states2count[cache.state] += 1
        total += 1

        function_id = get_job(job_id, db=db).command_desc
        # initialize record if not present
        if not function_id in function2state2count:
            function2state2count[function_id] = dict(list(map(lambda x: (x, 0), states_order)) + [("all", 0)])
        # update
        fss = function2state2count[function_id]
        fss[cache.state] += 1
        fss["all"] += 1

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
        (Cache.DONE, "done"),
        (Cache.FAILED, "failed"),
        (Cache.BLOCKED, "blocked"),
        (Cache.PROCESSING, "processing"),
        (Cache.NOT_STARTED, "to do"),
    ]

    totals = defaultdict(lambda: 0)
    for function_id in sorted(function2state2count):
        function_stats = function2state2count[function_id]
        alls = []
        for state, desc in states:
            num = function_stats[state]
            s = f"{num:5d} {desc}"
            if num > 0:
                s = compmake_colored(s, **Cache.state2color[state])
            else:
                s = " " * len(s)
            alls.append(s)
            totals[state] += num
        s = " ".join(alls)
        function_id_pad = (function_id + "()").ljust(flen)
        print(f"    {function_id_pad}: {s}")

    final = []
    for state, desc in states:
        s = f"{totals[state]:5d} {desc}"
        if totals[state] > 0:
            s = compmake_colored(s, **Cache.state2color[state])
        final.append(s)
    final = " ".join(final)
    print(f"    {'total'.rjust(flen)}: {final}.")
