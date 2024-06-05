""" The actual interface of some commands in commands.py """

from compmake import (
    CMJobID,
    COMMANDS_ADVANCED,
    CacheQueryDB,
    CompmakeBug,
    Context,
    all_jobs,
    get_job,
    job_exists,
    parse_job_list,
    ui_command,
    ui_error,
    ui_info,
)
from zuper_commons.types import ZAssertionError, add_context
from zuper_utils_asyncio import SyncTaskInterface


@ui_command(section=COMMANDS_ADVANCED, alias="check-consistency")
async def check_consistency(sti: SyncTaskInterface, args: list[str], context: Context, raise_if_error: bool = False) -> int:
    """Checks in the DB that the relations between jobs are consistent."""
    _ = sti
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


async def check_job(job_id: CMJobID, context: Context) -> tuple[bool, list[str]]:
    db = context.get_compmake_db()
    cq = CacheQueryDB(db)

    with add_context(op="check_job", job_id=job_id) as c:

        job = get_job(job_id, db)
        defined_by = job.defined_by
        assert "root" in defined_by

        c["job"] = job

        dparents = cq.direct_parents(job_id)
        dchildren = cq.direct_children(job_id)
        c["dparents"] = dparents
        c["dchildren"] = dchildren

        # all_parents = parents(job_id, db=db)
        # all_children = children(job_id, db=db)

        # print(job_id)
        # print('d children: %s' % dchildren)
        # print('all children: %s' % all_children)

        errors = []

        def e(msg, **kwargs):
            raise ZAssertionError(msg, **kwargs)
            errors.append(msg)

        for defb in defined_by:
            if defb == "root":
                continue
            if not job_exists(defb, db=db):
                s = f"{job_id!r} defined by {defined_by!r} but {defb!r} not existing."
                e(s)

        for dp in dparents:
            if not cq.job_exists(dp):
                s = f"Direct parent {dp!r} of {job_id!r} does not exist."
                e(s)
            else:
                if not job_id in cq.direct_children(dp):
                    s = f"{job_id!r} thinks {dp!r} is its direct parent;"
                    s += f"but {dp!r} does not think {job_id!r} is its direct child"
                    e(s)

        # for ap in all_parents:
        #     if not job_exists(ap, db=db):
        #         s = f"Parent {ap!r} of {job_id!r} does not exist."
        #         e(s)
        #     else:
        #         if not job_id in children(ap, db=db):
        #             e(f"{ap} is parent but no child relation")

        for dc in dchildren:
            if not cq.job_exists(dc):
                s = f"Direct child {dc!r} of {job_id!r} does not exist."
                e(s)
            else:
                dc_parents = cq.direct_parents(dc)
                if not job_id in dc_parents:
                    dc_job = cq.get_job(dc)
                    e(
                        f"{dc!r} is a direct child of {job_id!r} but no direct_parent relation",
                        job=job,
                        dc_job=dc_job,
                        dc_parents=dc_parents,
                    )

        # for ac in all_children:
        #     if not job_exists(ac, db=db):
        #         s = f"A child {ac!r} of {job_id!r} does not exist."
        #         e(s)
        #     else:
        #         if not job_id in parents(ac, db=db):
        #             e(f"{ac} is direct child but no parent relation")

        if errors:
            s = f"Inconsistencies for {job_id}:\n"
            s += "\n".join(f"- {msg}" for msg in errors)
            await ui_error(context, s)
            return False, errors
        else:
            return True, []
