# -*- coding: utf-8 -*-
from compmake.jobs.priority import compute_priorities
from compmake.ui.helpers import COMMANDS_ADVANCED, ui_command


@ui_command(section=COMMANDS_ADVANCED)
def debug_priority(non_empty_job_list, context, cq):  # @UnusedVariable
    """ Shows the priority of jobs. """
    jobs = list(non_empty_job_list)
    priorities = compute_priorities(all_targets=jobs, cq=cq)

    sorted_jobs = sorted(jobs, key=lambda x: priorities[x])
    for job_id in sorted_jobs:
        p = priorities[job_id]
        print('%5s %s' % (p, job_id))
