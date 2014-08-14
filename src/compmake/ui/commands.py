''' These are the commands available from the CLI.

There are 3 special variables:
- 'args': list of all command line arguments
- 'job_list': the remaining argument parsed as a job list.
- 'non_empty_job_list': same, but error if not specified.
'''

from .. import CompmakeConstants, get_compmake_config, get_compmake_status
from ..context import Context
from ..events import publish
from ..jobs import (ManagerLocal, MultiprocessingManager, PmakeManager, 
    SGEManager, all_jobs, clean_target, mark_remake, top_targets)
from ..structures import JobFailed, MakeFailed, ShellExitRequested, UserError
from ..ui import info
from ..utils import safe_pickle_dump
from .helpers import (ACTIONS, COMMANDS_ADVANCED, COMMANDS_CLUSTER, GENERAL, 
    ui_command, ui_section)
from contracts import contract


ui_section(GENERAL)


@ui_command(alias='quit')
def exit(context):  # @ReservedAssignment
    '''Exits Compmake's console.'''
    raise ShellExitRequested()
 

@ui_command(section=ACTIONS, dbchange=True)
def make(job_list, context, cq, new_process='config', recurse=False):
    '''Makes selected targets; or all targets if none specified. '''
    if new_process == 'config':
        new_process = get_compmake_config('new_process')
    return make_(context=context, cq=cq, job_list=job_list, recurse=recurse,
                 new_process=new_process)
    
@contract(context=Context)
def make_(context, cq, job_list, recurse, new_process):
    '''Makes selected targets; or all targets if none specified. '''
    # job_list = list(job_list) # don't ask me why XXX
    job_list = [x for x in job_list]

    db = context.get_compmake_db()
    if not job_list:
        job_list = list(top_targets(db=db))

    manager = ManagerLocal(context=context, cq=cq,
                           recurse=recurse, new_process=new_process)
    manager.add_targets(job_list)
    manager.process()
    return _raise_if_failed(manager)

def _raise_if_failed(manager):
    if manager.failed:

        raise MakeFailed(failed=manager.failed,
                         blocked=manager.blocked)
#         if manager.blocked:
#             msg = ('%d job(s) failed, %d job(s) blocked.' % 
#                     (len(manager.failed), len(manager.blocked)))
#         else:
#             msg =  ('%d job(s) failed.' % len(manager.failed))
# 
#         if len(manager.failed) < 5:
#             for f in manager.failed:
#                 msg += '\n- %s' % f
#         raise CommandFailed(msg)


@ui_command(section=COMMANDS_ADVANCED,  dbchange=True)
def delete(job_list, context):
    """ Remove completely the job from the DB. Useful for generated jobs ("delete not root"). """
    from compmake.jobs.storage import delete_all_job_data
    job_list = [x for x in job_list]

    db = context.get_compmake_db()
    for job_id in job_list:
        delete_all_job_data(job_id=job_id, db=db)

 

@ui_command(section=ACTIONS, dbchange=True)
def clean(job_list, context):
    ''' Cleans the result of the selected computation (or everything \
        if nothing specified). '''
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


# TODO: add hidden
@ui_command(section=COMMANDS_ADVANCED, dbchange=True)
def make_single(job_list, context, out_result):
    ''' Makes a single job -- not for users, but for slave mode. '''
    if len(job_list) > 1:
        raise UserError("I want only one job")

    from compmake.jobs import actions
    try:
        job_id = job_list[0]
        res = actions.make(job_id=job_id, context=context)
        print('Writing to %r' % out_result)
        safe_pickle_dump(res, out_result)
        return 0
    except JobFailed as e:
        res = dict(fail=str(e))
        print('Writing to %r' % out_result)
        safe_pickle_dump(res, out_result)

        # FIXME        
        return CompmakeConstants.RET_CODE_JOB_FAILED


@ui_command(section=ACTIONS, dbchange=True)
def parmake(job_list, context, cq, n=None, recurse=False, new_process='config'):    
    """ Parallel equivalent of "make", using multiprocessing.Process. (suggested)"""
    publish(context, 'parmake-status', status='Obtaining job list')
    job_list = list(job_list)
    
    if new_process == 'config':
        new_process = get_compmake_config('new_process')

    db = context.get_compmake_db()
    if not job_list:
        # XXX
        job_list = list(top_targets(db=db))

    publish(context, 'parmake-status',
            status='Starting multiprocessing manager (forking)')
    manager = PmakeManager(num_processes=n, 
                           context=context,
                           cq=cq, 
                           recurse=recurse,
                           new_process=new_process)

    publish(context, 'parmake-status', status='Adding %d targets.' % len(job_list))
    manager.add_targets(job_list)

    publish(context, 'parmake-status', status='Processing')
    manager.process()
 
    return _raise_if_failed(manager)

    

@ui_command(section=COMMANDS_ADVANCED, dbchange=True)
def parmake_pool(job_list, context, cq, n=None, recurse=False):
    '''Parallel equivalent of "make", using multiprocessing.Pool. (buggy)

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
    manager = MultiprocessingManager(num_processes=n,
                                     cq=cq,
                                     context=context, 
                                     recurse=recurse)

    publish(context, 'parmake-status', status='Adding %d targets.' % len(job_list))

    manager.add_targets(job_list)

    publish(context, 'parmake-status', status='Processing')
    manager.process()
    return _raise_if_failed(manager)



@ui_command(section=COMMANDS_CLUSTER, dbchange=True)
def sgemake(job_list, context, cq):
    ''' (experimental) SGE equivalent of "make". '''
    job_list = [x for x in job_list]

    if not job_list:
        db = context.get_compmake_db()
        job_list = list(top_targets(db=db))

    manager = SGEManager(context=context, cq=cq)
    manager.add_targets(job_list)
    manager.process()
    return _raise_if_failed(manager)
# 
# @ui_command(section=COMMANDS_CLUSTER, dbchange=True)
# def clustmake(job_list, context, cq):
#     ''' (experimental) Cluster equivalent of "make". '''
#     # job_list = list(job_list) # don't ask me why XXX
#     job_list = [x for x in job_list]
# 
#     if not job_list:
#         db = context.get_compmake_db()
#         job_list = list(top_targets(db))
# 
#     cluster_conf = get_compmake_config('cluster_conf')
# 
#     if not os.path.exists(cluster_conf):
#         msg = ('Configuration file %r does not exist.' % cluster_conf)
#         raise UserError(msg)
# 
#     hosts = parse_yaml_configuration(open(cluster_conf))
#     manager = ClusterManager(hosts=hosts, context=context, cq=cq)
#     manager.add_targets(job_list)
#     manager.process()
#     return _raise_if_failed(manager)


@ui_command(section=ACTIONS, dbchange=True)
def remake(non_empty_job_list, context, cq, new_process='config'):
    '''Remake the selected targets (equivalent to clean and make). '''

    non_empty_job_list = list(non_empty_job_list)

    if not ask_if_sure_remake(non_empty_job_list):
        return

    for job in non_empty_job_list:
        db = context.get_compmake_db()
        mark_remake(job, db=db)

    manager = ManagerLocal(context=context, cq=cq, new_process=new_process)
    manager.add_targets(non_empty_job_list)
    manager.process()
    return _raise_if_failed(manager)


def ask_if_sure_remake(non_empty_job_list):
    """ If interactive, ask the user yes or no. Otherwise returns True. """
    from ..ui.console import ask_question
    if get_compmake_status() == CompmakeConstants.compmake_status_interactive:
        question = ("Should I clean and remake %d jobs? [y/n] " % 
            len(non_empty_job_list))
        answer = ask_question(question)
        if not answer:
            info('Not cleaned.')
            return False
        else:
            return True
    return True


@ui_command(section=ACTIONS, dbchange=True)
def parremake(non_empty_job_list, context, cq):
    '''Parallel equivalent of "remake". '''
    db = context.get_compmake_db()
    non_empty_job_list = list(non_empty_job_list)

    if not ask_if_sure_remake(non_empty_job_list):
        return

    for job in non_empty_job_list:
        mark_remake(job, db=db)

    manager = PmakeManager(context=context, cq=cq)
    manager.add_targets(non_empty_job_list)
    manager.process()
    return _raise_if_failed(manager)

