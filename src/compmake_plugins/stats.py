""" The actual interface of some commands in commands.py """
from collections import defaultdict
from typing import Dict

from compmake import (
    Cache,
    compmake_colored,
    CompmakeConstants,
    get_job,
    get_job_cache,
    parse_job_list,
    ui_command,
    VISUALIZATION,
)
from compmake.utils import pad_to_screen
from zuper_utils_asyncio import SyncTaskInterface


@ui_command(section=VISUALIZATION)
async def stats(sti: SyncTaskInterface, args, context, cq):
    """Displays a coarse summary of the jobs state."""
    if not args:
        job_list = cq.all_jobs()
    else:
        job_list = parse_job_list(args, context=context, cq=cq)

    job_list = list(job_list)
    CompmakeConstants.aliases["last"] = job_list
    display_stats(job_list, context)


def display_stats(job_list, context):
    db = context.get_compmake_db()
    states_order = [
        Cache.NOT_STARTED,
        # Cache.IN_PROGRESS,
        Cache.FAILED,
        Cache.BLOCKED,
        Cache.DONE,
    ]
    # initialize counters to 0
    states2count = dict(list(map(lambda x: (x, 0), states_order)))

    function2state2count: Dict[str, Dict[str, int]] = {}
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
        function2state2count[function_id][cache.state] += 1
        function2state2count[function_id]["all"] += 1

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
        #         (Cache.IN_PROGRESS, 'in progress'),
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
            alls.append(s)
            totals[state] += num
        s = ",".join(alls)
        function_id_pad = (function_id + "()").ljust(flen)
        print(f"    {function_id_pad}: {s}.")

    final = []
    for state, desc in states:
        s = f"{totals[state]:5d} {desc}"
        if totals[state] > 0:
            s = compmake_colored(s, **Cache.state2color[state])
        final.append(s)
    final = ",".join(final)
    print(f"    {'total'.rjust(flen)}: {final}.")
