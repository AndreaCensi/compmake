''' The actual interface of some commands in commands.py '''
from time import time

from compmake.structures import Cache
from compmake.utils.visualization import duration_human, colored

from compmake.jobs.queries import direct_parents, direct_children
from compmake.jobs.storage import get_job_cache, all_jobs
from compmake.jobs.uptodate import up_to_date
from compmake.ui.helpers import padleft, ui_command, VISUALIZATION
import sys

         
@ui_command(section=VISUALIZATION, alias='ls')
def list(job_list):
    '''Lists the status of the selected targets (or all targets \
if not specified).
    
    If only one job is specified, then it is listed in more detail.  '''
    if not job_list:
        job_list = all_jobs()
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
        s += " " * (50 - len(s))
        cache = get_job_cache(job_id)
        tag = '%s/%s' % (Cache.state2desc[cache.state], up) 
        
        k = (cache.state, up)
        assert k in state2color, "I found strange state %s" % k
        color_args = state2color[k]
        s += colored(tag, **color_args)
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
    bold = lambda x:  colored(padleft(15, x), attrs=['bold'])
    
    
    try:
        print bold('Job ID: ') + '%s' % job_id 
        print bold('Status: ') + '%s' % Cache.state2desc[cache.state]
        print bold('Uptodate: ') + '%s (%s)' % (up, reason)
        print bold('Children: ') + '%s' % ', '.join(children)
        print bold('Parents: ') + '%s' % ', '.join(parents)
        
        #if cache.state == Cache.DONE:
            #print bold('Time: ') 

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
          
