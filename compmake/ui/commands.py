''' These are the commands available from the CLI.

There are 3 special variables:
- 'args': list of all command line arguments
- 'job_list': the remaining argument parsed as a job list.
- 'non_empty_job_list': same, but error if not specified.
''' 
from . import (ui_command, GENERAL, ACTIONS, PARALLEL_ACTIONS,
               COMMANDS_ADVANCED, COMMANDS_CLUSTER, ui_section)
from .. import (RET_CODE_JOB_FAILED, get_compmake_status,
    compmake_status_interactive)
from ..config import compmake_config
from ..jobs import (all_jobs, ClusterManager, ManagerLocal,
    MultiprocessingManager, clean_target, mark_remake, mark_more, top_targets,
    parse_yaml_configuration)
from ..structures import UserError, JobFailed, ShellExitRequested
from ..utils import info
import os


ui_section(GENERAL)


@ui_command(alias='quit')
def exit():  # @ReservedAssignment
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

    job_list = list(job_list)
    
    if not job_list:
        job_list = list(all_jobs())
        
    if not job_list:
        return 
    
    from ..ui.console import ask_question
    
    if get_compmake_status() == compmake_status_interactive: 
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
    job_list = list(job_list)
    
    if not job_list:
        job_list = list(top_targets())
    
    #print "Making %d jobs" % len(job_list)
    
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
    job_list = list(job_list)
    
    if not job_list:
        job_list = list(top_targets())
    
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
    
    job_list = list(job_list)
    
    if not job_list:
        job_list = list(top_targets())    
        
    cluster_conf = compmake_config.cluster_conf  # @UndefinedVariable

    if not os.path.exists(cluster_conf):
        raise UserError('Configuration file "%s" does not exist.' 
                        % cluster_conf)    
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
    cluster_conf = compmake_config.cluster_conf  # @UndefinedVariable
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
    
    non_empty_job_list = list(non_empty_job_list) 
            
    from ..ui.console import ask_question
    if get_compmake_status() == compmake_status_interactive: 
        question = "Should I clean and remake %d jobs? [y/n] " % \
            len(non_empty_job_list)
        answer = ask_question(question)
        if not answer:
            info('Not cleaned.')
            return
        
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
    
    non_empty_job_list = list(non_empty_job_list)
    
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
    
    non_empty_job_list = list(non_empty_job_list)
    
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
    
    non_empty_job_list = list(non_empty_job_list)
    
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
    

