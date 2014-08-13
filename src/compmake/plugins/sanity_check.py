''' The actual interface of some commands in commands.py '''
from ..jobs import (direct_parents, parents, direct_children, children, all_jobs,
    parse_job_list)
from ..ui import error, ui_command, COMMANDS_ADVANCED


@ui_command(section=COMMANDS_ADVANCED, alias='check-consistency')
def check_consistency(args, context, cq):  # @ReservedAssignment
    ''' Checks in the DB that the relations between jobs are consistent. '''
    if not args:
        job_list = cq.all_jobs()
    else:
        job_list = parse_job_list(args, context=context, cq=cq)

    for job_id in job_list:
        check_job(job_id, context)

    return 0


def check_job(job_id, context):
    db = context.get_compmake_db()
    dparents = direct_parents(job_id, db=db)
    all_parents = parents(job_id, db=db)
    dchildren = direct_children(job_id, db=db)
    all_children = children(job_id, db=db)
    
    errors = []

    def e(msg):
        errors.append(msg)
        
    for dp in dparents:
        if not job_id in direct_children(dp, db=db):
            e('%s is direct parent but no direct child relation' % dp)
    
    for ap in all_parents:
        if not job_id in children(ap, db=db):
            e('%s is parent but no child relation' % ap)
    
    for dc in dchildren:
        if not job_id in direct_parents(dc, db=db):
            e('%s is direct child but no direct_parent relation' % dc)
            
    for ac in all_children:
        if not job_id in parents(ac, db=db):
            e('%s is direct child but no direct_parent relation' % ac)
            
    if errors:
        s = ('Inconsistencies for %s:\n' % job_id)
        s += '\n'.join('- %s' % msg for msg in errors)
        error(s)

    
    


