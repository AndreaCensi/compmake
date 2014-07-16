''' These are the commands available from the CLI.

There are 3 special variables:
- 'args': list of all command line arguments
- 'job_list': the remaining argument parsed as a job list.
- 'non_empty_job_list': same, but error if not specified.
'''
import os

from contracts import contract

from . import (GENERAL, ACTIONS, PARALLEL_ACTIONS, COMMANDS_ADVANCED,
    COMMANDS_CLUSTER, ui_section)
from .. import CompmakeConstants, get_compmake_status, get_compmake_config
from ..context import Context
from ..events import publish
from ..jobs import (all_jobs, ClusterManager, ManagerLocal,
    MultiprocessingManager, clean_target, mark_remake, top_targets,
    parse_yaml_configuration, SGEManager)
from ..structures import UserError, JobFailed, ShellExitRequested
from ..ui import info
from .helpers import ui_command
from compmake.jobs.manager_pmake import PmakeManager


ui_section(GENERAL)


@ui_command(alias='quit')
def exit(context):  # @ReservedAssignment
    '''Exits the shell.'''
    raise ShellExitRequested()
 

@ui_command(section=ACTIONS)
def clean(job_list, context):
    '''Cleans the result of the selected computation \
(or everything is nothing specified). '''
    db = context.get_compmake_db()

    # job_list = list(job_list) # don't ask me why XXX
    job_list = [x for x in job_list]

    if not job_list:
        job_list = list(all_jobs(db=db))

    if not job_list:
        return

    from ..ui import ask_question

    # Use context
    if get_compmake_status() == CompmakeConstants.compmake_status_interactive:
        question = "Should I clean %d jobs? [y/n] " % len(job_list)
        answer = ask_question(question)
        if not answer:
            info('Not cleaned.')
            return

    for job_id in job_list:
        clean_target(job_id, db=db)


# FIXME BUG: "make failed" == "make all" if no failed

@contract(context=Context)
def make_(context, job_list, recurse=False):
    '''Makes selected targets; or all targets if none specified. '''
    # job_list = list(job_list) # don't ask me why XXX
    job_list = [x for x in job_list]

    db = context.get_compmake_db()
    if not job_list:
        job_list = list(top_targets(db=db))

    manager = ManagerLocal(context=context, recurse=recurse)
    manager.add_targets(job_list)
    manager.process()

    if manager.failed:
        return('%d job(s) failed.' % len(manager.failed))
    else:
        return 0


@ui_command(section=ACTIONS)
def delete(job_list, context):
    """ Remove completely the job from the DB. Useful for generated jobs ("delete not root"). """
    from compmake.jobs.storage import delete_all_job_data
    job_list = [x for x in job_list]

    db = context.get_compmake_db()
    for job_id in job_list:
        delete_all_job_data(job_id=job_id, db=db)


@ui_command(section=ACTIONS)
def make(job_list, context, recurse=False):
    '''Makes selected targets; or all targets if none specified. '''
    return make_(context=context, job_list=job_list, recurse=recurse)


# TODO: add hidden
@ui_command(section=COMMANDS_ADVANCED)
def make_single(job_list, context):
    ''' Makes a single job -- not for users, but for slave mode. '''
    if len(job_list) > 1:
        raise UserError("I want only one job")

    from compmake import jobs
    try:
        job_id = job_list[0]
        jobs.make(job_id, context=context)
        return 0
    except JobFailed:
        return CompmakeConstants.RET_CODE_JOB_FAILED


@ui_command(section=PARALLEL_ACTIONS)
def parmake(job_list, context, n=None, recurse=False):
    '''Parallel equivalent of "make".

Usage:
       
       parmake [n=<num>] [joblist]
 '''
    
    publish(context, 'parmake-status', status='Obtaining job list')
    job_list = list(job_list)

    db = context.get_compmake_db()
    if not job_list:
        job_list = list(top_targets(db=db))

    publish(context, 'parmake-status',
            status='Starting multiprocessing manager (forking)')
    manager = MultiprocessingManager(num_processes=n, context=context, recurse=recurse)

    publish(context, 'parmake-status', status='Adding %d targets.' % len(job_list))
#     logger.info('Adding %d targets ' % len(job_list))
    manager.add_targets(job_list)

    publish(context, 'parmake-status', status='Processing')
    manager.process()

    if manager.failed:
        if manager.blocked:
            return ('%d job(s) failed, %d job(s) blocked.' % 
                    (len(manager.failed), len(manager.blocked)))
        else:
            return ('%d job(s) failed.' % len(manager.failed))
    else:
        return 0



@ui_command(section=PARALLEL_ACTIONS)
def pmake(job_list, context, n=None, recurse=False):    
    """ Parallel processing using multiprocessing.Process. """
    publish(context, 'parmake-status', status='Obtaining job list')
    job_list = list(job_list)

    db = context.get_compmake_db()
    if not job_list:
        job_list = list(top_targets(db=db))

    publish(context, 'parmake-status',
            status='Starting multiprocessing manager (forking)')
    manager = PmakeManager(num_processes=n, context=context, recurse=recurse)

    publish(context, 'parmake-status', status='Adding %d targets.' % len(job_list))
    manager.add_targets(job_list)

    publish(context, 'parmake-status', status='Processing')
    manager.process()

    if manager.failed:
        if manager.blocked:
            return ('%d job(s) failed, %d job(s) blocked.' % 
                    (len(manager.failed), len(manager.blocked)))
        else:
            return ('%d job(s) failed.' % len(manager.failed))
    else:
        return 0
    

@ui_command(section=COMMANDS_CLUSTER)
def clustmake(job_list, context):
    '''
        Cluster equivalent of "make".
    '''
    # job_list = list(job_list) # don't ask me why XXX
    job_list = [x for x in job_list]

    if not job_list:
        db = context.get_compmake_db()
        job_list = list(top_targets(db))

    cluster_conf = get_compmake_config('cluster_conf')

    if not os.path.exists(cluster_conf):
        msg = ('Configuration file %r does not exist.' % cluster_conf)
        raise UserError(msg)

    hosts = parse_yaml_configuration(open(cluster_conf))
    manager = ClusterManager(hosts=hosts, context=context)
    manager.add_targets(job_list)
    manager.process()

    if manager.failed:
        return('%d job(s) failed.' % len(manager.failed))
    else:
        return 0



@ui_command(section=COMMANDS_CLUSTER)
def sgemake(job_list, context):
    '''
        SGE equivalent of "make".
     '''
    job_list = [x for x in job_list]

    if not job_list:
        db = context.get_compmake_db()
        job_list = list(top_targets(db=db))

    manager = SGEManager(context=context)
    manager.add_targets(job_list)
    manager.process()

    if manager.failed:
        return('%d job(s) failed.' % len(manager.failed))
    else:
        return 0


@ui_command(section=ACTIONS)
def remake(non_empty_job_list, context):
    '''Remake the selected targets (equivalent to clean and make). '''

    non_empty_job_list = list(non_empty_job_list)

    if not ask_if_sure_remake(non_empty_job_list):
        return

    for job in non_empty_job_list:
        db = context.get_compmake_db()
        mark_remake(job, db=db)

    manager = ManagerLocal(context=context)
    manager.add_targets(non_empty_job_list)
    manager.process()

    if manager.failed:
        return('%d job(s) failed.' % len(manager.failed))
    else:
        return 0


def ask_if_sure_remake(non_empty_job_list):
    """ If interactive, ask the user yes or no. Otherwise returns True. """
    from ..ui.console import ask_question
    if get_compmake_status() == CompmakeConstants.compmake_status_interactive:
        question = "Should I clean and remake %d jobs? [y/n] " % \
            len(non_empty_job_list)
        answer = ask_question(question)
        if not answer:
            info('Not cleaned.')
            return False
        else:
            return True
    return True


@ui_command(section=PARALLEL_ACTIONS)
def parremake(non_empty_job_list, context):
    '''Parallel equivalent of "remake". '''
    db = context.get_compmake_db()
    non_empty_job_list = list(non_empty_job_list)

    if not ask_if_sure_remake(non_empty_job_list):
        return

    for job in non_empty_job_list:
        mark_remake(job, db=db)

    manager = MultiprocessingManager(context=context)
    manager.add_targets(non_empty_job_list)
    manager.process()

    if manager.failed:
        return('%d job(s) failed.' % len(manager.failed))
    else:
        return 0

