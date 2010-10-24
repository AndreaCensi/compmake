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
        
    job_list.sort()
    
    if len(job_list) == 1:
        list_job_detail(job_list[0])
    else:
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
        
        tag =  Cache.state2desc[cache.state]
        
        if not up:
            tag += ' (needs update)' 
        
        k = (cache.state, up)
        assert k in state2color, "I found strange state %s" % k
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
        
def list_job_detail(job_id):
    #computation = get_computation(job_id)
    cache = get_job_cache(job_id)     
    parents = direct_parents(job_id)
    children = direct_children(job_id)
    up, reason = up_to_date(job_id)

    red = lambda x: colored(x, 'red')
    bold = lambda x:  colored(rjust(x + ' ', 15), attrs=['bold'])
    
    
    try:
        print bold('Job ID:') + '%s' % job_id 
        print bold('Status:') + '%s' % Cache.state2desc[cache.state]
        print bold('Uptodate:') + '%s (%s)' % (up, reason)
        print bold('Children:') + '%s' % ', '.join(children)
        print bold('Parents:') + '%s' % ', '.join(parents)
        
        if cache.state == Cache.DONE and cache.done_iterations > 1:
            print bold('Iterations:') + '%s' % cache.done_iterations 
            print bold('Wall Time:') + '%.4f s' % cache.walltime_used 
            print bold('CPU Time:') + '%.4f s' % cache.cputime_used
            print bold('Host:') + '%s' % cache.host

        if cache.state == Cache.IN_PROGRESS:
            print bold('Progress:') + '%s/%s' % \
                (cache.iterations_in_progress, cache.iterations_goal)
        

        if cache.state == Cache.FAILED:
            print red(cache.exception)
            print red(cache.backtrace)
            
        def display_with_prefix(buffer, prefix,
                                transform=lambda x:x, out=sys.stdout):
            for line in buffer.split('\n'):
                out.write('%s%s\n' % (prefix, transform(line)))
                
        if cache.captured_stdout:
            print "-----> captured stdout <-----"
            display_with_prefix(cache.captured_stdout, prefix='|',
                                transform=lambda x: colored(x, attrs=['dark']))
            
        if cache.captured_stderr:
            print "-----> captured stderr <-----"
            display_with_prefix(cache.captured_stdout, prefix='|',
                                transform=lambda x: colored(x, attrs=['dark']))
            
    except AttributeError:
        pass
          
