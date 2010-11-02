''' These are the commands available from the CLI.

There are 3 special variables:
- 'args': list of all command line arguments
- 'job_list': the remaining argument parsed as a job list.
- 'non_empty_job_list': same, but error if not specified.
''' 

import sys, os
from compmake.ui.helpers import   ui_section, ui_command, \
    GENERAL, ACTIONS, PARALLEL_ACTIONS, COMMANDS_ADVANCED, \
    COMMANDS_CLUSTER
from compmake.jobs import clean_target, mark_remake, mark_more, top_targets    
from compmake.jobs.storage import  all_jobs 
from compmake.structures import   UserError, JobFailed, ShellExitRequested
from compmake.config import compmake_config 

from compmake.jobs.cluster_conf import parse_yaml_configuration
from compmake.utils.visualization import info
from compmake.jobs.manager_local import ManagerLocal
from compmake.jobs.manager_multiprocessing import MultiprocessingManager
from compmake.jobs.manager_ssh_cluster import ClusterManager
from compmake import RET_CODE_JOB_FAILED



ui_section(GENERAL)

@ui_command(alias='quit')
def exit():
    '''Exits the shell.'''
    raise ShellExitRequested()

#@ui_command(section=ACTIONS)
#def check():
#    '''Makes sure that the cache is sane. '''
#    make_sure_cache_is_sane()

@ui_command(section=ACTIONS)
def clean(job_list):
    '''Cleans the result of the selected computation \
(or everything is nothing specified). '''
    if not job_list: 
        job_list = all_jobs()
    
    # convert to list
    job_list = list(job_list)
    
    if not job_list:
        return 
    
    from compmake.ui.console import ask_question
    
    if compmake_config.interactive: #@UndefinedVariable
        question = "Should I clean %d jobs? [y/n] " % len(job_list)
        answer = ask_question(question)
        if not answer:
            info('Not cleaned.')
            return
        
    for job_id in job_list:
        clean_target(job_id)
   
 
@ui_command(section=ACTIONS)
def make(job_list):
    '''Makes selected targets; or all targets if none specified. ''' 
    if not job_list:
        job_list = top_targets()
        
    manager = ManagerLocal()
    manager.add_targets(job_list)
    manager.process()

    if manager.failed:
        return RET_CODE_JOB_FAILED
    else:
        return 0

# TODO: add hidden
@ui_command(section=COMMANDS_ADVANCED)
def make_single(job_list, more=False):
    ''' Makes a single job -- not for users, but for slave mode. '''
    if len(job_list) > 1:
        raise UserError("I want only one job")
    
    from compmake import jobs
    try:
        job_id = job_list[0]
        if more:
            mark_more(job_id)
        jobs.make(job_id, more)
        return 0
    except JobFailed:
        return RET_CODE_JOB_FAILED

# TODO: add num processors
@ui_command(section=PARALLEL_ACTIONS)
def parmake(job_list, n=None):
    '''Parallel equivalent of "make".

Usage:
       
       parmake [n=<num>] [joblist]
 '''
    if not job_list:
        job_list = top_targets()
    
    manager = MultiprocessingManager(n)
    manager.add_targets(job_list, more=False)
    manager.process()
    
    if manager.failed:
        return RET_CODE_JOB_FAILED
    else:
        return 0

@ui_command(section=COMMANDS_CLUSTER)
def clustmake(job_list):
    '''Cluster equivalent of "make".

       Note: you should use the Redis backend to use multiprocessing.
 '''
    if not job_list:
        job_list = top_targets()
    
    cluster_conf = compmake_config.cluster_conf #@UndefinedVariable

    if not os.path.exists(cluster_conf):
        raise UserError('Configuration file "%s" does not exist.' % cluster_conf)    
    hosts = parse_yaml_configuration(open(cluster_conf))
    manager = ClusterManager(hosts)
    manager.add_targets(job_list)
    manager.process()
    
    if manager.failed:
        return RET_CODE_JOB_FAILED
    else:
        return 0


@ui_command(section=COMMANDS_CLUSTER)
def clustmore(non_empty_job_list, loop=1):
    '''Cluster equivalent of "more".

       Note: you should use the Redis backend to use multiprocessing.
 ''' 
    cluster_conf = compmake_config.cluster_conf #@UndefinedVariable
    hosts = parse_yaml_configuration(open(cluster_conf))
    
    for x in range(int(loop)):
        if loop > 1:
            info("------- more: iteration %d --- " % x) 

        for job in non_empty_job_list:
            mark_more(job)
            
            manager = ClusterManager(hosts)
        manager.add_targets(non_empty_job_list, more=True)
        manager.process()
        
        if manager.failed:
            return RET_CODE_JOB_FAILED
        
    return 0

@ui_command(section=ACTIONS)
def remake(non_empty_job_list):  
    '''Remake the selected targets (equivalent to clean and make). '''
    for job in non_empty_job_list:
        mark_remake(job)
    
    manager = ManagerLocal()
    manager.add_targets(non_empty_job_list)
    manager.process()
    
    if manager.failed:
        return RET_CODE_JOB_FAILED
    else:
        return 0

@ui_command(section=PARALLEL_ACTIONS)
def parremake(non_empty_job_list):
    '''Parallel equivalent of "remake". '''
    for job in non_empty_job_list:
        mark_remake(job)
        
    manager = MultiprocessingManager()
    manager.add_targets(non_empty_job_list, more=True)
    manager.process()

    if manager.failed:
        return RET_CODE_JOB_FAILED
    else:
        return 0

@ui_command(section=ACTIONS) 
def more(non_empty_job_list, loop=1):
    '''Makes more of the selected targets. '''
    
    for x in range(int(loop)):
        if loop > 1:
            info("------- more: iteration %d --- " % x) 

        for job in non_empty_job_list:
            mark_more(job)
            
        manager = ManagerLocal()
        manager.add_targets(non_empty_job_list, more=True)
        manager.process()
        
        if manager.failed:
            return RET_CODE_JOB_FAILED

    return 0

@ui_command(section=PARALLEL_ACTIONS)
def parmore(non_empty_job_list, loop=1):
    '''Parallel equivalent of "more". '''
    for job in non_empty_job_list:
        mark_more(job)
        
    for x in range(int(loop)):
        if loop > 1:
            info("------- parmore: iteration %d --- " % x) 

        for job in non_empty_job_list:
            mark_more(job)

        manager = MultiprocessingManager()
        manager.add_targets(non_empty_job_list, more=True)
        manager.process()
        
        if manager.failed:
            return RET_CODE_JOB_FAILED

    return 0
    

