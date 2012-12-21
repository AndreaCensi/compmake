''' The actual interface of some commands in commands.py '''
from ..jobs import get_job_cache, all_jobs, get_job, parse_job_list
from ..structures import Cache
from ..ui import ui_command, VISUALIZATION
from ..utils import  pad_to_screen
import string
from compmake.ui.visualization import compmake_colored


state2color = {
    Cache.NOT_STARTED: {'color': 'yellow'}, #{'attrs': ['dark']},
    Cache.IN_PROGRESS: {'color': 'yellow'},
    Cache.BLOCKED: {'color': 'yellow'},
    Cache.FAILED: {'color': 'red'},
    Cache.DONE: {'color': 'green'},
}


@ui_command(section=VISUALIZATION)
def stats(args):
    '''Displays a coarse summary of the jobs state. '''
    if not args:
        job_list = all_jobs()
    else:
        job_list = parse_job_list(args)

    display_stats(job_list)


def display_stats(job_list):

    states_order = [Cache.NOT_STARTED, Cache.IN_PROGRESS,
                    Cache.FAILED, Cache.BLOCKED, Cache.DONE]
    # initialize counters to 0
    states2count = dict(map(lambda x: (x, 0), states_order))

    function2state2count = {}
    total = 0

    for job_id in job_list:

        cache = get_job_cache(job_id)
        states2count[cache.state] += 1
        total += 1

        function_id = get_job(job_id).command_desc
        # initialize record if not present
        if not function_id in function2state2count:
            function2state2count[function_id] = \
                dict(map(lambda x: (x, 0), states_order) + [('all', 0)])
        # update
        function2state2count[function_id][cache.state] += 1
        function2state2count[function_id]['all'] += 1

        if total == 100: # XXX: use standard method
            print("Loading a large number of jobs...\r")

    if total == 0:
        print(pad_to_screen('No jobs found.'))
        return

    print("Found %s jobs in total. Summary by state:    " % total)

    for state in states_order:
        desc = "%30s" % Cache.state2desc[state]
        # colorize output
        desc = compmake_colored(desc, **state2color[state])

        num = states2count[state]
        if num > 0:
            print("%s: %5d" % (desc, num))

    print("Summary by function:")

    flen = max(len(x) for x in function2state2count)
    for function_id, function_stats in function2state2count.items():

        states = [(Cache.DONE, 'done'),
                  (Cache.FAILED, 'failed'),
                  (Cache.BLOCKED, 'blocked'),
                  #(Cache.MORE_REQUESTED, 'done'),
                  (Cache.IN_PROGRESS, 'in progress'),
                  (Cache.NOT_STARTED, 'to do'),
                  ]

        alls = []
        for state, desc in states:
            num = function_stats[state]
            desc = Cache.state2desc[state]
            s = '%5d %s' % (num, desc)
            if num > 0:
                s = compmake_colored(s, **state2color[state])
            alls.append(s)

        s = ",".join(alls)
        function_id_pad = string.rjust(function_id, flen)
        print("    %s(): %s." % (function_id_pad, s))




