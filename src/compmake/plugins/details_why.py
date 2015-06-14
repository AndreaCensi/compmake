from compmake.ui.helpers import ui_command, VISUALIZATION
from compmake.jobs.storage import job_cache_exists, get_job_cache


@ui_command(section=VISUALIZATION)
def why(non_empty_job_list, context, cq):
    """ Shows the last line of the error """
    num = 0
    for job_id in non_empty_job_list:
        details_why_one(job_id, context, cq)
        num += 1


def details_why_one(job_id, context, cq):
    db = context.get_compmake_db()

    if job_cache_exists(job_id, db):
        cache = get_job_cache(job_id, db)
        why = str(cache.exception)
        lines = why.split('\n')
        one = lines[0]
        if len(lines) > 1:
            one += ' ... +%d lines' % (len(lines)-1)
        print('%20s: %s' %(job_id, one))  
