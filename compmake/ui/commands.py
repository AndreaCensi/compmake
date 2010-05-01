''' These are the commands available from the CLI.

There are 3 special variables:
- 'args': list of all command line arguments
- 'job_list': the remaining argument parsed as a job list.
- 'non_empty_job_list': same, but error if not specified.
'''
 
from compmake.utils import  info 
from compmake.ui.helpers import   ui_section, ui_command, \
    GENERAL, ACTIONS, VISUALIZATION, PARALLEL_ACTIONS
from compmake.ui.commands_impl import list_jobs 
from compmake.jobs import make_sure_cache_is_sane, \
    clean_target, make_targets, mark_remake, mark_more, top_targets, parmake_targets
from compmake.jobs.storage import get_job_cache, all_jobs 
from compmake.structures import  Cache


class ShellExitRequested(Exception):
    pass


ui_section(GENERAL)

@ui_command(alias='quit')
def exit():
    '''Exits the shell.'''
    raise ShellExitRequested()

#@ui_command(section=ACTIONS)
def check():
    '''Makes sure that the cache is sane '''
    make_sure_cache_is_sane()

@ui_command(section=ACTIONS)
def clean(job_list):
    '''Cleans the result of the selected computation (or everything is nothing specified) '''
    if not job_list: 
        job_list = all_jobs()
        
    for job_id in job_list:
        clean_target(job_id)
   

@ui_command(section=VISUALIZATION)
def list_failed(job_list):
    '''Lists the jobs that have failed. '''
    if not job_list:
        job_list = all_jobs()
    job_list.sort()
    
    job_list = [job_id for job_id in job_list \
                if get_job_cache(job_id).state == Cache.FAILED]
    
    list_jobs(job_list)
      
@ui_command(section=ACTIONS)
def make(job_list):
    '''Makes selected targets; or all targets if none specified ''' 
    if not job_list:
        job_list = top_targets()
    make_targets(job_list)

@ui_command(section=PARALLEL_ACTIONS)
def parmake(job_list):
    '''Parallel equivalent of "make".

       Note: you should use the Redis backend to use multiprocessing.
 '''
    if not job_list:
        job_list = top_targets()
    
    parmake_targets(job_list)

@ui_command(section=ACTIONS)
def remake(non_empty_job_list):  
    '''Remake the selected targets (equivalent to clean and make). '''
    for job in non_empty_job_list:
        mark_remake(job)
        
    make_targets(non_empty_job_list)

@ui_command(section=PARALLEL_ACTIONS)
def parremake(non_empty_job_list):
    '''Parallel equivalent of "remake". '''
    for job in non_empty_job_list:
        mark_remake(job)
        
    parmake_targets(non_empty_job_list)

@ui_command(section=ACTIONS) 
def more(non_empty_job_list):
    '''Makes more of the selected targets. '''
    
    for job in non_empty_job_list:
        mark_more(job)
        
    make_targets(non_empty_job_list, more=True)

@ui_command(section=PARALLEL_ACTIONS)
def parmore(non_empty_job_list):
    '''Parallel equivalent of "more". '''
    for job in non_empty_job_list:
        mark_more(job)
        
    parmake_targets(non_empty_job_list, more=True)

@ui_command(section=PARALLEL_ACTIONS)
def parmoreconf(non_empty_job_list):
    '''Makes more of the selected target, in an infinite loop '''
    for i in range(100000):
        info("------- parmorecont: iteration %d --- " % i) 
        for job in non_empty_job_list:
            mark_more(job)
        parmake_targets(non_empty_job_list, more=True)
    
@ui_command(section=VISUALIZATION)
def stats():
    '''Prints statistics about the jobs loaded'''
    njobs = len(all_jobs())
    print("%d jobs loaded." % njobs)
    # Add class report    

