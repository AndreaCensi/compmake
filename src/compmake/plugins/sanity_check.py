# -*- coding: utf-8 -*-
""" The actual interface of some commands in commands.py """
from ..jobs import (children, direct_children, direct_parents, parents,
                    parse_job_list)
from ..ui import COMMANDS_ADVANCED, ui_command
from compmake.exceptions import CompmakeBug
from compmake.ui.visualization import error
from contracts import contract
from compmake.jobs.storage import get_job, job_exists, all_jobs


@ui_command(section=COMMANDS_ADVANCED, alias='check-consistency')
def check_consistency(args, context, cq,
                      raise_if_error=False):  # @ReservedAssignment
    """ Checks in the DB that the relations between jobs are consistent. """
    
    db = context.get_compmake_db()
 
    # Do not use cq
    if not args:
        job_list = all_jobs(db=db)
    else:
        job_list = parse_job_list(args, context=context)

    job_list = list(job_list)
    #print('Checking consistency of %d jobs.' % len(job_list))
    errors = {}
    for job_id in job_list:
        try:
            ok, reasons = check_job(job_id, context)
            if not ok:
                errors[job_id] = reasons
        except CompmakeBug as e:
            errors[job_id] = ['bug: %s' % e]
            
    if errors:
        msg = "Inconsistency with %d jobs:" % len(errors)
        for job_id, es in errors.items():
            msg += '\n- job %r:\n%s' % (job_id, '\n'.join(es))
            
        if raise_if_error: 
            raise CompmakeBug(msg)
        else:
            error(msg)

    return 0

@contract(returns='tuple(bool, list(str))')
def check_job(job_id, context):
    db = context.get_compmake_db()
    
    job = get_job(job_id, db)
    defined_by = job.defined_by
    assert 'root' in defined_by
    
    dparents = direct_parents(job_id, db=db)
    all_parents = parents(job_id, db=db)
    dchildren = direct_children(job_id, db=db)
    all_children = children(job_id, db=db)

    #print(job_id)
    #print('d children: %s' % dchildren)
    #print('all children: %s' % all_children)
    
    errors = []

    def e(msg):
        errors.append(msg)
    
    for defb in defined_by:
        if defb == 'root': continue
        if not job_exists(defb, db=db):
            s = ('%r defined by %r but %r not existing.'
                 %(job_id, defined_by, defb))
            e(s) 


    for dp in dparents:
        
        if not job_exists(dp, db=db):
            s = 'Direct parent %r of %r does not exist.' % (dp, job_id)
            e(s)
        else:
            if not job_id in direct_children(dp, db=db):
                s = '%s thinks %s is its direct parent;' % (job_id, dp)
                s += 'but %s does not think %s is its direct child' % (dp, job_id)
                e(s)

    for ap in all_parents:
        if not job_exists(ap, db=db):
            s = 'Parent %r of %r does not exist.' % (ap, job_id)
            e(s)
        else:
            if not job_id in children(ap, db=db):
                e('%s is parent but no child relation' % ap)

    for dc in dchildren:
        if not job_exists(dc, db=db):
            s = 'Direct child %r of %r does not exist.' % (dc, job_id)
            e(s)
        else:
            if not job_id in direct_parents(dc, db=db):
                e('%s is direct child but no direct_parent relation' % dc)

    for ac in all_children:
        if not job_exists(ac, db=db):
            s = 'A child %r of %r does not exist.' % (ac, job_id)
            e(s)
        else:
            if not job_id in parents(ac, db=db):
                e('%s is direct child but no parent relation' % ac)

    if errors:
        s = ('Inconsistencies for %s:\n' % job_id)
        s += '\n'.join('- %s' % msg for msg in errors)
        error(s)
        return False, errors
    else:
        return True, []
