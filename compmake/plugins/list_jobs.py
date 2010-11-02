''' The actual interface of some commands in commands.py '''
from time import time

from compmake.structures import Cache
from compmake.utils.visualization import duration_human, colored

from compmake.jobs.queries import direct_parents, direct_children
from compmake.jobs.storage import get_job_cache, all_jobs
from compmake.jobs.uptodate import up_to_date
from compmake.ui.helpers import  ui_command, VISUALIZATION
import sys
from compmake.jobs.syntax.parsing import parse_job_list
from string import rjust

         
@ui_command(section=VISUALIZATION, alias='ls')
def list(args):
    '''Lists the status of the selected targets (or all targets \
if not specified).
    
    If only one job is specified, then it is listed in more detail.  '''
    if not args:
        job_list = all_jobs()
    else:
        job_list = parse_job_list(args)
      
    # no -- for performance reasons  
    # job_list.sort()
    
#    if len(job_list) == 1:
#        list_job_detail(job_list[0])
#    else:
    # print "obtained", job_list
    list_jobs(job_list)         

state2color = {
        # The ones commented out are not possible
        # (Cache.NOT_STARTED, True): None,
        (Cache.NOT_STARTED, False): {'attrs':['dark']},
        # (Cache.IN_PROGRESS, True): None,
        (Cache.IN_PROGRESS, False): {'color':'yellow'},
        (Cache.MORE_REQUESTED, True): {'color': 'blue'},
        (Cache.MORE_REQUESTED, False): {'color':'green', 'on_color':'on_red'},
        #(Cache.FAILED, True): None,
        (Cache.FAILED, False): {'color':'red'},
        (Cache.DONE, True): {'color':'green'},
        (Cache.DONE, False): {'color':'magenta'},
}


def list_jobs(job_list):
    for job_id in job_list:
        up, reason = up_to_date(job_id)
        s = job_id
        s += " " + (" " * (60 - len(s)))
        cache = get_job_cache(job_id)
        
        tag = Cache.state2desc[cache.state]
        
        #if not up:
        #    tag += ' (needs update)' 
        
        k = (cache.state, up)
        assert k in state2color, "I found strange state %s" % str(k)
        color_args = state2color[k]
        s += colored(tag, **color_args)
        if cache.state == Cache.DONE and cache.done_iterations > 1:
            s += ' %s iterations completed ' % cache.done_iterations 
        if cache.state == Cache.IN_PROGRESS:
            s += ' (%s/%s iterations in progress) ' % \
                (cache.iterations_in_progress, cache.iterations_goal)
        if up:
            when = duration_human(time() - cache.timestamp)
            s += " (%s ago)" % when
        else:
            if cache.state in [Cache.DONE, Cache.MORE_REQUESTED]:
                s += " (needs update: %s)" % reason 
        print s
        
