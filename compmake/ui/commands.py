''' These are the commands available from the CLI.

There are 3 special variables:
- 'args': list of all command line arguments
- 'job_list': the remaining argument parsed as a job list.
- 'non_empty_job_list': same, but error if not specified.
''' 
from compmake.ui.helpers import   ui_section, ui_command, \
    GENERAL, ACTIONS, VISUALIZATION, PARALLEL_ACTIONS, COMMANDS_ADVANCED, \
    COMMANDS_CLUSTER
from compmake.ui.commands_impl import list_jobs 
from compmake.jobs import make_sure_cache_is_sane, \
    clean_target, mark_remake, mark_more, top_targets    
from compmake.jobs.storage import get_job_cache, all_jobs 
from compmake.structures import  Cache, UserError, JobFailed
from compmake.config import compmake_config, show_config, config_switches, \
    set_config_from_strings

from compmake.jobs.cluster_conf import parse_yaml_configuration
from compmake.utils.visualization import info
from compmake.jobs.manager_local import ManagerLocal
from compmake.jobs.manager_multiprocessing import MultiprocessingManager
from compmake.jobs.manager_ssh_cluster import ClusterManager
import sys
from compmake.config.config_html import create_config_html
from compmake.ui.commands_html import create_commands_html
from compmake import RET_CODE_JOB_FAILED
import os


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
    '''Cleans the result of the selected computation \
(or everything is nothing specified) '''
    if not job_list: 
        job_list = all_jobs()
        
    if not job_list:
        return 
    
    from compmake.ui.console import ask_question
    
    if compmake_config.interactive: #@UndefinedVariable
        question = "Should I clean %d jobs?" % len(job_list)
        answer = ask_question(question)
        if not answer:
            info('Not cleaned.')
            return
        
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
    ''' Makes a single job -- not for users, but for slave mode '''
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


@ui_command(section=PARALLEL_ACTIONS)
def parmake(job_list):
    '''Parallel equivalent of "make".

       Note: you should use the Redis backend to use multiprocessing.
 '''
    if not job_list:
        job_list = top_targets()
    
    manager = MultiprocessingManager()
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

    
        #make_targets(non_empty_job_list, more=True)

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
   
@ui_command(section=VISUALIZATION)
def stats():
    '''Prints statistics about the jobs loaded'''
    njobs = len(all_jobs())
    print("%d jobs loaded." % njobs)
    # TODO: Add class report    


@ui_command(section=GENERAL)
def config(args):
    ''' Get/set configuration parameters '''    
    if not args:
        # show
        show_config(sys.stdout)
        return
        
    name = args.pop(0)
    if not args:
        if not name in config_switches:
            raise UserError("I don't know the switch '%s'." % name)
        info('config %s %s' % (name, compmake_config.__dict__[name]))
        return
        
    set_config_from_strings(name, args)


@ui_command(section=COMMANDS_ADVANCED)
def config_html(output_file=''):
    ''' Dumps the config description in html on the specified file '''
    if output_file:
        f = open(output_file, 'w')
    else:
        f = sys.stdout
    create_config_html(f)
    

@ui_command(section=COMMANDS_ADVANCED)
def commands_html(output_file=''):
    ''' Dumps the commands description in html on the specified file '''
    if output_file:
        f = open(output_file, 'w')
    else:
        f = sys.stdout
    create_commands_html(f)
