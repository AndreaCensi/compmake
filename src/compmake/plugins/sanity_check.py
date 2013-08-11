''' The actual interface of some commands in commands.py '''
from ..jobs import (direct_parents, parents, direct_children, children, all_jobs,
    parse_job_list)
from ..ui import ui_command, VISUALIZATION
from ..ui.visualization import error


@ui_command(section=VISUALIZATION, alias='check-consistency')
def check_consistency(args):  # @ReservedAssignment
    ''' Checks that the relations between jobs are consistent. '''
    if not args:
        job_list = all_jobs()
    else:
        job_list = parse_job_list(args)

    check_jobs(job_list)
    return 0


def check_jobs(job_list):
    for job_id in job_list:
        check_job(job_id)

        
def check_job(job_id):
    dparents = direct_parents(job_id)
    all_parents = parents(job_id)
    dchildren = direct_children(job_id)
    all_children = children(job_id)
    
    errors = []

    def e(msg):
        errors.append(msg)
        
    for dp in dparents:
        if not job_id in direct_children(dp):
            e('%s is direct parent but no direct child relation' % dp)
    
    for ap in all_parents:
        if not job_id in children(ap):
            e('%s is parent but no child relation' % ap)
    
    for dc in dchildren:
        if not job_id in direct_parents(dc):
            e('%s is direct child but no direct_parent relation' % dc)
            
    for ac in all_children:
        if not job_id in parents(ac):
            e('%s is direct child but no direct_parent relation' % ac)
            
    if errors:
        s = ('Inconsistencies for %s:\n' % job_id)
        s += '\n'.join('- %s' % msg for msg in errors)
        error(s)

    
    


