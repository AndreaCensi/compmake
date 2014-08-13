''' The actual interface of some commands in commands.py '''
import string
from time import time

from ..jobs import parse_job_list
from ..structures import Cache
from ..ui import compmake_colored, ui_command, VISUALIZATION
from ..utils import duration_human
from ..jobs.syntax.parsing import is_root_job,  aliases


@ui_command(section=VISUALIZATION, alias='list')
def ls(args, context, cq, complete_names=False):  # @ReservedAssignment
    ''' Lists the status of the selected targets (or all targets if not specified).
    
        If only one job is specified, then it is listed in more detail.  
    '''
    
    if not args:
        job_list = cq.all_jobs()
    else:
        job_list = parse_job_list(tokens=args, context=context, cq=cq)
        
    job_list = list(job_list)
    aliases['last'] = job_list
    list_jobs(context, job_list, cq=cq, complete_names=complete_names)
    return 0


state2color = {
        # The ones commented out are not possible
        # (Cache.NOT_STARTED, True): None,
        (Cache.NOT_STARTED, False): {},  # 'attrs': ['dark']},
        # (Cache.IN_PROGRESS, True): None,
        (Cache.IN_PROGRESS, False): {'color': 'yellow'},
        # (Cache.FAILED, True): None,
        (Cache.FAILED, False): {'color': 'red'},
        (Cache.BLOCKED, True): {'color': 'yellow'},
        (Cache.BLOCKED, False): {'color': 'yellow'},  # XXX
        (Cache.DONE, True): {'color': 'green'},
        (Cache.DONE, False): {'color': 'magenta'},
}

 


def list_jobs(context, job_list, cq, complete_names=False):
    job_list = list(job_list)
    # print('%s jobs in total' % len(job_list))
    if not job_list:
        print('No jobs found.')
        return

    # maximum job length
    
    max_len = 100
    def format_job_id(job_id):
        if complete_names or len(job_id) < max_len:
            return job_id
        else:
            b = 15
            r = max_len - b - len(' ... ')
            return job_id[:15] + ' ... ' + job_id[-r:] 
    
    
    jlen = max(len(format_job_id(x)) for x in job_list)

    cpu_total = []
    wall_total = []
    for job_id in job_list:
        cache = cq.get_job_cache(job_id)

        # TODO: only ask up_to_date if necessary
        up, reason, _ = cq.up_to_date(job_id)

        job = cq.get_job(job_id)
         

        Mmin = 4
        M = 40
        if jlen < M:
            indent = M - jlen
        else:
            indent = Mmin
        s = " " * indent 
        
        is_root = is_root_job(job)
        if not is_root:
            s += '%d ' % (len(job.defined_by) - 1)
        else:
            s += '  '

        s += string.ljust(format_job_id(job_id), jlen) + '  '

        tag = Cache.state2desc[cache.state]

        # if not up:
        #    tag += ' (needs update)' 

        k = (cache.state, up)
        assert k in state2color, "I found strange state %s" % str(k)

        s += compmake_colored(tag, **state2color[k])

        if up:
            wall_total.append(cache.walltime_used)
            cpu = cache.cputime_used
            cpu_total.append(cpu)
            s += ' %5.2f m ' % (cpu / 60.0)
            when = duration_human(time() - cache.timestamp)
            s += " (%s ago)" % when
        else:
            if cache.state in [Cache.DONE]:
                s += " (needs update: %s)" % reason

            if cache.state == Cache.FAILED:
                when = duration_human(time() - cache.timestamp)
                s += " (%s ago)" % when

        print(s)

    if cpu_total:
        print('  total  CPU time: %s.' % duration_human(sum(cpu_total)))
        print('        wall time: %s.' % duration_human(sum(wall_total)))

