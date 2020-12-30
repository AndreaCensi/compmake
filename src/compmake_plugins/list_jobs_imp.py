""" The actual interface of some commands in commands.py """
import os
from time import time
from typing import Dict, List, Sequence, Tuple

from compmake import (
    compmake_colored,
    job_args_sizeof,
    job_cache_exists,
    job_cache_sizeof,
    job_userobject_exists,
    job_userobject_sizeof,
)
from compmake import CompmakeConstants
from compmake import ui_command, VISUALIZATION
from compmake import is_root_job, parse_job_list
from compmake import Cache, cache_has_large_overhead, timing_summary
from compmake.utils import TableFormatter
from compmake.utils import get_screen_columns
from compmake import ui_message
from zuper_commons.ui import duration_compact

# red, green, yellow, blue, magenta, cyan, white.


# if False:
#     format_utility_job = dict(color="white", attrs=["concealed"])
#     format_separator = dict(color="white", attrs=["concealed"])
#     format_when = dict(color="white", attrs=["concealed"])
# else:
format_utility_job = dict()
format_separator = dict()
format_when = dict()


@ui_command(section=VISUALIZATION, alias="list")
def ls(args, context, cq, complete_names=False, reason=False, all_details=False):  # @ReservedAssignment
    """
        Lists the status of the given jobs (or all jobs if none specified
        specified).

        Options:

            ls complete_names=1   # do not abbreviate names
            ls reason=1  # show why jobs are not uptodate
    """

    if not args:
        job_list = cq.all_jobs()
    else:
        job_list = parse_job_list(tokens=args, context=context, cq=cq)

    job_list = list(job_list)
    CompmakeConstants.aliases["last"] = job_list
    list_jobs(context, job_list, cq=cq, complete_names=complete_names, reason=reason, all_details=all_details)
    return 0


# @contract(objects="seq[N](unicode)", returns="tuple(unicode, list[N](unicode), unicode)")
def minimal_names(objects: Sequence[str]) -> Tuple[str, List[str], str]:
    """
        Converts a list of object IDs to a minimal non-ambiguous list of names.

        For example, the names: ::

            test_learn_fast_10
            test_learn_slow_10
            test_learn_faster_10

        is converted to: ::

            fast
            slow
            faster

        Returns prefix, minimal, postfix
    """
    if len(objects) == 1:
        return "", list(objects), ""

    # find the common prefix
    prefix = os.path.commonprefix(objects)
    # invert strings
    objects_i = [o[::-1] for o in objects]
    # find postfix
    postfix = os.path.commonprefix(objects_i)[::-1]
    #     print(objects)
    #     print('prefix: %r post: %r' % (prefix, postfix))
    n1 = len(prefix)
    n2 = len(postfix)
    # remove it
    minimal = [o[n1 : len(o) - n2] for o in objects]

    # recreate them to check everything is ok
    objects2 = [prefix + m + postfix for m in minimal]

    # print objects, objects2
    assert objects == objects2, (prefix, minimal, postfix)
    return prefix, minimal, postfix


def list_jobs(context, job_list, cq, complete_names=False, all_details=False, reason=False):
    job_list = list(job_list)
    # print('%s jobs in total' % len(job_list))
    if not job_list:
        string = "No jobs found."
        ui_message(context, string)
        return

    # maximum job length

    max_len = 100

    def format_job_id(ajob_id):
        if complete_names or len(ajob_id) < max_len:
            return ajob_id
        else:
            b = 15
            r = max_len - b - len(" ... ")
            return ajob_id[:15] + " ... " + ajob_id[-r:]

    # abbreviates the names
    #     if not complete_names:
    #         prefix, abbreviated, postfix = minimal_names(job_list)
    #         job_list = abbreviated

    jlen = max(len(format_job_id(x)) for x in job_list)

    cpu_total = []
    wall_total = []

    tf = TableFormatter(sep="  ")

    for job_id in job_list:
        tf.row()

        cache = cq.get_job_cache(job_id)

        # TODO: only ask up_to_date if necessary
        up, up_reason, up_ts = cq.up_to_date(job_id)

        job = cq.get_job(job_id)

        is_root = is_root_job(job)
        if not is_root:
            msg = (job_id, job, job.defined_by)
            assert len(job.defined_by) >= 1, msg
            assert job.defined_by[0] == "root", msg

            level = len(job.defined_by) - 1
            assert level >= 1
            tf.cell("%d" % level)
        else:
            tf.cell("")

        if job.needs_context:
            tf.cell("d")
        else:
            tf.cell("")

        job_name_formatted = format_job_id(job_id).ljust(jlen)

        # de-emphasize utility jobs
        is_utility = "context" in job_id or "dynrep" in job_id
        if is_utility:
            job_name_formatted = compmake_colored(job_name_formatted, **format_utility_job)

        tf.cell(format_job_id(job_id))

        tag = Cache.state2desc[cache.state]

        k = (cache.state, up)
        assert k in Cache.stateupdate2color, "I found strange state %s" % str(k)

        tag_s = compmake_colored(tag, **Cache.stateupdate2color[k])
        if not up and cache.state in [Cache.DONE, Cache.FAILED]:
            tag_s += "*"
        tf.cell(tag_s)

        if reason:
            tf.cell(up_reason)
            tf.cell(duration_compact(time() - up_ts))

        db = context.get_compmake_db()
        sizes = get_sizes(job_id, db=db)
        size_s = format_size(sizes["total"])
        tf.cell(size_s)

        if cache.state in [Cache.DONE]:
            wall_total.append(cache.walltime_used)
            cpu = cache.cputime_used
            cpu_total.append(cpu)

            if cpu > 5 or cache_has_large_overhead(cache) or all_details:  # TODO: add param
                # s_cpu = duration_compact(cpu)
                s_cpu = timing_summary(cache)
            else:
                s_cpu = ""

            tf.cell(s_cpu)

        else:
            tf.cell("")  # cpu

        if cache.state in [Cache.DONE, Cache.FAILED]:
            when = duration_compact(time() - cache.timestamp)
            when_s = f"({when} ago)"

            when_s = compmake_colored(when_s, **format_when)

            tf.cell(when_s)
        else:
            tf.cell("")  # when

    tf.done()

    ind = "  "

    do_one_column = len(job_list) <= 5

    if do_one_column:
        for line in tf.get_lines():
            string = ind + line
            ui_message(context, string)
    else:
        linewidth = get_screen_columns()
        # print('*'*linewidth)
        # sep = '   ' + compmake_colored('|', color='white', attrs=['dark']) + '   '
        sep = "   " + compmake_colored("|", **format_separator) + "   "

        for line in tf.get_lines_multi(linewidth - len(ind), sep=sep):
            string = ind + line
            ui_message(context, string)
    if cpu_total:
        cpu_time = duration_compact(sum(cpu_total))
        wall_time = duration_compact(sum(wall_total))
        string = f" total {len(job_list)} jobs   CPU time: {cpu_time}   wall: {wall_time}"
        # print(scpu)
        ui_message(context, string)


def format_size(nbytes: int) -> str:
    if nbytes == 0:
        return ""
    if nbytes < 1024 * 1024:  # TODO: add param
        return ""
    mb = float(nbytes) / (1024 * 1024)
    return f"{mb:.2f} MB"


def get_sizes(job_id, db) -> Dict:
    """ Returns byte sizes for jobs pieces.

        Returns dict with keys 'args','cache','result','total'.
    """
    res = {}
    res["args"] = job_args_sizeof(job_id, db)

    if job_cache_exists(job_id, db):
        res["cache"] = job_cache_sizeof(job_id, db)
    else:
        res["cache"] = 0

    if job_userobject_exists(job_id, db):
        res["result"] = job_userobject_sizeof(job_id, db)
    else:
        res["result"] = 0

    res["total"] = res["cache"] + res["args"] + res["result"]
    return res