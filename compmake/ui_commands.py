''' These are the commands available from the CLI '''

from compmake.process import make_targets, mark_more, mark_remake,\
    top_targets, parmake_targets, make_sure_cache_is_sane, \
     clean_target, all_targets, up_to_date
from compmake.process_storage import get_job_cache
from visualization import  duration_human

def check():
    ''' Makes sure that the cache is sane '''
    make_sure_cache_is_sane()

def clean(job_list):
    ''' Cleans the result of the selected computation (or everything is nothing specified) '''
    if not job_list: 
        job_list = all_targets()
        
    for job_id in job_list:
        clean_target(job_id)
            
def list(job_list):
    ''' Lists the status of the selected targets (or all targets if not specified) '''
    if not job_list:
        job_list = all_targets()
    job_list.sort()
    
    list_jobs(job_list)
         
def make(job_list):
    ''' Makes selected targets; or all targets if none specified ''' 
    if not job_list:
        job_list = top_targets()
    make_targets(job_list)

def parmake(job_list):
    ''' Parallel equivalent of 'make' '''
    if not job_list:
        job_list = top_targets()
    
    parmake_targets(job_list)
  
def remake(non_empty_job_list):  
    ''' Remake the selected targets (equivalent to clean and make) '''
    for job in non_empty_job_list:
        mark_remake(job)
        
    make_targets(non_empty_job_list)
                
def parremake(non_empty_job_list):
    ''' Parallel equivalent of remake '''
    for job in non_empty_job_list:
        mark_remake(job)
        
    parmake_targets(non_empty_job_list)
    
def more(non_empty_job_list):
    ''' Makes more of the selected targets '''
    
    for job in non_empty_job_list:
        mark_more(job)
        
    make_targets(non_empty_job_list, more=True)


def parmore(non_empty_job_list):
    ''' Parallel equivalent of more '''
    for job in non_empty_job_list:
        mark_more(job)
        
    parmake_targets(non_empty_job_list, more=True)

def parmoreconf(non_empty_job_list):
    ''' Makes more of the selected target, in an infinite loop '''
    for i in range(100000):
        print "------- parmorecont: iteration %d --- \n" % i 
        for job in non_empty_job_list:
            mark_more(job)
        parmake_targets(non_empty_job_list, more=True)
        
        

from compmake.structures import Cache
from time import time

def list_jobs(job_list):
    for job_id in job_list:
        up, reason = up_to_date(job_id)
        s = job_id
        s += " " * (50-len(s))
        cache = get_job_cache(job_id)
        s += Cache.state2desc[cache.state]
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
            
    
    
