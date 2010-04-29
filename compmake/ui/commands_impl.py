''' The actual interface of some commands in commands.py '''

from compmake.structures import Cache
from time import time
from compmake.utils.visualization import duration_human
from compmake.jobs.queries import direct_parents, direct_children
from compmake.jobs.storage import get_job_cache
from compmake.jobs.uptodate import up_to_date

def list_jobs(job_list):
    for job_id in job_list:
        up, reason = up_to_date(job_id)
        s = job_id
        s += " " * (50 - len(s))
        cache = get_job_cache(job_id)
        s += Cache.state2desc[cache.state]
        s += '/%s' % up
        if up:
            when = duration_human(time() - cache.timestamp)
            s += " (%s ago)" % when
        else:
            if cache.state in [Cache.DONE, Cache.MORE_REQUESTED]:
                s += " (needs update: %s)" % reason 
        print s
        
        if cache.state == Cache.FAILED:
            print cache.exception
            print cache.backtrace

def list_job_detail(job_id):
    #computation = get_computation(job_id)
    cache = get_job_cache(job_id)     
    needed_by = direct_parents(job_id)
    depends_on = direct_children(job_id)
    print 'Job name: %s' % job_id 
    print 'Status: %s' % Cache.state2desc[cache.state]
    print 'Direct children: %s' % depends_on
    print 'Direct parents: %s' % needed_by
    
          
