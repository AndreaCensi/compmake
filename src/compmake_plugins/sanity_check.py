""" The actual interface of some commands in commands.py """

from typing import List, Tuple

from compmake import (
    all_jobs,
    children,
    CMJobID,
    COMMANDS_ADVANCED,
    CompmakeBug,
    Context,
    direct_children,
    direct_parents,
    get_job,
    job_exists,
    parents,
    parse_job_list,
    ui_command,
    ui_error,
    ui_info,
)
from zuper_utils_asyncio import SyncTaskInterface


@ui_command(section=COMMANDS_ADVANCED, alias="check-consistency")
async def check_consistency(sti: SyncTaskInterface, args: List[str], context: Context, raise_if_error: bool = False) -> int:
    """Checks in the DB that the relations between jobs are consistent."""

    db = context.get_compmake_db()

    # Do not use cq
    if not args:
        job_list = all_jobs(db=db)
    else:
        job_list = parse_job_list(args, context=context)

    job_list = list(job_list)
    # print('Checking consistency of %d jobs.' % len(job_list))
    errors = {}
    for job_id in job_list:
        try:
            ok, reasons = await check_job(job_id, context)
            if not ok:
                errors[job_id] = reasons
        except CompmakeBug as e:
            errors[job_id] = ["bug: %s" % e]

    if errors:
        msg = f"Inconsistency with {len(errors)} jobs:"
        for job_id, es in errors.items():
            msg += "\n- job %r:\n%s" % (job_id, "\n".join(es))
        msg += "\n"
        if raise_if_error:
            raise CompmakeBug(msg)
        else:
            await ui_error(context, msg)
    else:
        msg = "No inconsistencies found."
        await ui_info(context, msg)
    return 0


async def check_job(job_id: CMJobID, context: Context) -> Tuple[bool, List[str]]:
    db = context.get_compmake_db()

    job = get_job(job_id, db)
    defined_by = job.defined_by
    assert "root" in defined_by

    dparents = direct_parents(job_id, db=db)
    all_parents = parents(job_id, db=db)
    dchildren = direct_children(job_id, db=db)
    all_children = children(job_id, db=db)

    # print(job_id)
    # print('d children: %s' % dchildren)
    # print('all children: %s' % all_children)

    errors = []

    def e(msg):
        errors.append(msg)

    for defb in defined_by:
        if defb == "root":
            continue
        if not job_exists(defb, db=db):
            s = "%r defined by %r but %r not existing." % (job_id, defined_by, defb)
            e(s)

    for dp in dparents:
        if not job_exists(dp, db=db):
            s = f"Direct parent {dp!r} of {job_id!r} does not exist."
            e(s)
        else:
            if not job_id in direct_children(dp, db=db):
                s = f"{job_id} thinks {dp} is its direct parent;"
                s += f"but {dp} does not think {job_id} is its direct child"
                e(s)

    for ap in all_parents:
        if not job_exists(ap, db=db):
            s = f"Parent {ap!r} of {job_id!r} does not exist."
            e(s)
        else:
            if not job_id in children(ap, db=db):
                e(f"{ap} is parent but no child relation")

    for dc in dchildren:
        if not job_exists(dc, db=db):
            s = f"Direct child {dc!r} of {job_id!r} does not exist."
            e(s)
        else:
            if not job_id in direct_parents(dc, db=db):
                e(f"{dc} is direct child but no direct_parent relation")

    for ac in all_children:
        if not job_exists(ac, db=db):
            s = f"A child {ac!r} of {job_id!r} does not exist."
            e(s)
        else:
            if not job_id in parents(ac, db=db):
                e(f"{ac} is direct child but no parent relation")

    if errors:
        s = f"Inconsistencies for {job_id}:\n"
        s += "\n".join(f"- {msg}" for msg in errors)
        await ui_error(context, s)
        return False, errors
    else:
        return True, []
