""" The actual interface of some commands in commands.py """
from ..jobs import (children, direct_children, direct_parents, parents,
                    parse_job_list)
from ..ui import COMMANDS_ADVANCED, ui_command
from compmake.exceptions import CompmakeBug
from compmake.ui.visualization import error
from contracts import contract


@ui_command(section=COMMANDS_ADVANCED, alias='check-consistency')
def check_consistency(args, context, cq,
                      raise_if_error=False):  # @ReservedAssignment
    """ Checks in the DB that the relations between jobs are consistent. """
    if not args:
        job_list = cq.all_jobs()
    else:
        job_list = parse_job_list(args, context=context, cq=cq)

    job_list = list(job_list)
    print('Checking consistency of %d jobs.' % len(job_list))
    errors = {}
    for job_id in job_list:
        ok, reasons = check_job(job_id, context)
        if not ok:
            errors[job_id] = reasons

    if raise_if_error and errors:
        msg = "Inconsistency with %d jobs:\n" % len(errors)
        for job_id, es in errors.items():
            msg += '\n- job %s:\n%s' % (job_id, '\n'.join(es))
        raise CompmakeBug(msg)

    return 0


@contract(returns='tuple(bool, list(str))')
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
            s = '%s thinks %s is its direct parent;' % (job_id, dp)
            s += 'but %s does not think %s is its direct child' % (dp, job_id)
            e(s)

    for ap in all_parents:
        if not job_id in children(ap, db=db):
            e('%s is parent but no child relation' % ap)

    for dc in dchildren:
        if not job_id in direct_parents(dc, db=db):
            e('%s is direct child but no direct_parent relation' % dc)

    for ac in all_children:
        if not job_id in parents(ac, db=db):
            e('%s is direct child but no parent relation' % ac)

    if errors:
        s = ('Inconsistencies for %s:\n' % job_id)
        s += '\n'.join('- %s' % msg for msg in errors)
        error(s)
        return False, errors
    else:
        return True, []
