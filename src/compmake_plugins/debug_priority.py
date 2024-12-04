from compmake import CacheQueryDB, COMMANDS_ADVANCED, compute_priorities, ui_command


@ui_command(section=COMMANDS_ADVANCED)
async def debug_priority(sti, non_empty_job_list, context, cq: CacheQueryDB) -> None:
    """Shows the priority of jobs."""
    jobs = list(non_empty_job_list)
    with cq.session() as cqs:
        priorities = compute_priorities(all_targets=jobs, cqs=cqs)

    sorted_jobs = sorted(jobs, key=lambda x: priorities[x])
    for job_id in sorted_jobs:
        p = priorities[job_id]
        print("%5s %s" % (p, job_id))
