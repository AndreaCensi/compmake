''' The actual interface of some commands in commands.py '''
from ..jobs import parse_job_list
from ..jobs.storage import (job_args_sizeof, job_cache_exists, job_cache_sizeof, 
    job_userobject_exists, job_userobject_sizeof)
from ..jobs.syntax.parsing import  is_root_job
from ..structures import Cache
from ..ui import VISUALIZATION, compmake_colored, ui_command
from ..utils import duration_compact
from contracts import contract
from time import time
from compmake.constants import CompmakeConstants



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
    CompmakeConstants.aliases['last'] = job_list
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

 
def list_jobs(context, job_list, cq, complete_names=False):  # @UnusedVariable
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
        
        if job.needs_context:
            s += 'd '
        else:
            s += '  '
            
        job_name_formatted = format_job_id(job_id).ljust(jlen)
        
        # de-emphasize utility jobs
        is_utility = 'context' in job_id or 'dynrep' in job_id
        if is_utility:
            job_name_formatted = compmake_colored(job_name_formatted,
                                                  'white', 
                                                  attrs=['dark'])
            
        s += job_name_formatted + '  '

        tag = Cache.state2desc[cache.state]
 
        k = (cache.state, up)
        assert k in state2color, "I found strange state %s" % str(k)

        s += compmake_colored('%7s' % tag, **state2color[k])

        db = context.get_compmake_db()
        sizes = get_sizes(job_id, db=db)
        s += '%10s ' % format_size(sizes['total'])
        if up:
            wall_total.append(cache.walltime_used)
            cpu = cache.cputime_used
            cpu_total.append(cpu)
            
            if cpu > 5: # TODO: add param
                s_cpu = duration_compact(cpu)
            else:
                s_cpu = ''
            s+= ' ' + s_cpu.rjust(10) + ' '
            
            when = duration_compact(time() - cache.timestamp)
            s += " (%s ago)" % when
        else:
            if cache.state in [Cache.DONE]:
                s += " (needs update: %s)" % reason

            if cache.state == Cache.FAILED:
                age = time() - cache.timestamp
                when = duration_compact(age)
                age_str = " (%s ago)" % when
                
                s += age_str.rjust(10)

        print(s)

    if cpu_total:
        cpu_time = duration_compact(sum(cpu_total))
        wall_time = duration_compact(sum(wall_total))
        scpu = (' total %d jobs   CPU time: %s   wall: %s' % (len(job_list), cpu_time, wall_time))
        print(scpu)

def format_size(nbytes):
    if nbytes == 0:
        return ''
    if nbytes < 1000*1000:  # TODO: add param
        return ''
    mb = float(nbytes) / (1000 * 1000)
    return '%d MB'% mb

@contract(returns='dict')
def get_sizes(job_id, db):
    """ Returns byte sizes for jobs pieces. 
    
        Returns dict with keys 'args','cache','result','total'.
    """
    res = {}
    res['args'] = job_args_sizeof(job_id, db)

    if job_cache_exists(job_id, db):
        res['cache'] = job_cache_sizeof(job_id, db)
    else:
        res['cache'] = 0

    if job_userobject_exists(job_id, db):
        res['result'] = job_userobject_sizeof(job_id, db)
    else: 
        res['result'] = 0
         
    res['total'] = res['cache'] + res['args'] + res['result']
    return res







