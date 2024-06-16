""" The actual interface of some commands in commands.py """

from compmake import (
    CMJobID,
    Cache,
    CacheQueryDB,
    VISUALIZATION,
    children,
    compmake_colored,
    get_job,
    get_job_args,
    get_job_cache,
    job_args_sizeof,
    job_cache_exists,
    job_cache_sizeof,
    job_userobject_exists,
    job_userobject_sizeof,
    ui_command,
)
from zuper_commons.types import check_isinstance
from zuper_commons.ui import size_compact
from zuper_typing import debug_print
from .console_output import write_line_endl


@ui_command(section=VISUALIZATION, alias="lsl")
async def details(sti, non_empty_job_list, context, cq, max_lines=None):
    """Shows the details for the given jobs including
    dependencies and stderr/stdout.

    The stderr/stdout lines are truncated. Use the ``max_lines``
    argument to see more:

        details max_lines=1000
    """
    num = 0
    for job_id in non_empty_job_list:
        # insert a separator if there is more than one job
        if num > 0:
            print("-" * 74)
        list_job_detail(job_id, context, cq, max_lines=max_lines)
        num += 1


def list_job_detail(job_id: CMJobID, context, cq: CacheQueryDB, max_lines):
    db = context.get_compmake_db()

    dparents = cq.direct_parents(job_id)
    all_parents = cq.parents(job_id)
    other_parents = set(all_parents) - set(dparents)

    # TODO: use quicker up to date
    up, reason, _ = cq.up_to_date(job_id)

    red = lambda x: compmake_colored(x, "red")
    bold = lambda x: compmake_colored((x + " ").rjust(15), attrs=["bold"])

    def format_list(x):
        return "\n- ".join([""] + sorted(x))

    job = get_job(job_id, db=db)
    # TODO: make it work in Python3K
    print(bold("Job ID:") + f"{job_id}")
    print(bold("Defined by:") + f"{job.defined_by}")
    # logger.info(job=job.__dict__)
    print(bold("needs_context:") + f"{job.needs_context}")

    dchildren = cq.direct_children(job_id)
    print(bold("Dependencies: (direct)") + f" ({len(dchildren)}) " + format_list(dchildren))

    all_children = children(job_id, db=db)  # XXX
    other_children = set(all_children) - set(dchildren)
    print(bold("Dependencies: (other)") + " (%d) " % len(other_children) + format_list(other_children))

    print(bold("Dependencies: (dynamic)") + f"{job.dynamic_children}")

    print(bold("Depending on this (direct):") + format_list(dparents))
    print(bold("Depending on this (other):") + format_list(other_parents))

    if job_cache_exists(job_id, db=db):
        cache2 = get_job_cache(job_id, db=db)

        print(debug_print(cache2))

        print(bold("Status:") + "%s" % Cache.state2desc[cache2.state])
        print(bold("Uptodate:") + "%s (%s)" % (up, reason))
        if cache2.walltime_used:
            print(bold("Wall Time:") + "%.4f s" % cache2.walltime_used)
        if cache2.cputime_used:
            print(bold("CPU Time:") + "%.4f s" % cache2.cputime_used)

        print("making: %s" % cache2.int_make)
        print("-- load: %s" % cache2.int_load_results)
        print("-- comp: %s" % cache2.int_compute)
        print("--   GC: %s" % cache2.int_gc)
        print("-- save: %s" % cache2.int_save_results)

        print(bold("Host:") + "%s" % cache2.host)

        if cache2.ti is not None:
            print(cache2.ti.pretty(show_wall=True, show_thread=True))

        if cache2.state == Cache.DONE:  # and cache.done_iterations > 1:
            # print(bold('Iterations:') + '%s' % cache.done_iterations)

            if not job_userobject_exists(job_id, db):
                print(red("inconsistent DB: user object does not exist."))

    else:
        print(bold("Status:") + "%s" % Cache.state2desc[Cache.NOT_STARTED])
        cache2 = None

    jobargs_size = job_args_sizeof(job_id, db)
    print(bold("      args size: ") + size_compact(jobargs_size))

    if job_cache_exists(job_id, db):
        cache_size = job_cache_sizeof(job_id, db)
        print(bold("     cache size: ") + size_compact(cache_size))
    else:
        cache_size = 0

    if job_userobject_exists(job_id, db):
        userobject_size = job_userobject_sizeof(job_id, db)
        print(bold("userobject size: ") + size_compact(userobject_size))
    else:
        userobject_size = 0

    total = jobargs_size + cache_size + userobject_size
    print(bold("          Total: ") + "%s" % size_compact(total))

    def display_with_prefix(buffer, prefix="", transform=lambda x: x):  # @ReservedAssignment
        check_isinstance(buffer, str)
        lines = buffer.splitlines()
        if max_lines is not None:
            if len(lines) > max_lines:
                warn = ".... Showing only last %d lines of %d ... " % (max_lines, len(lines))
                lines = [warn] + lines[-max_lines:]

        for line in lines:
            s = "%s%s" % (prefix, transform(line))
            write_line_endl(s)
            # if six.PY2:
            # s = s.encode('utf-8')
            # sys.stdout.buffer.write(s)

    if cache2 is not None:
        stdout = cache2.captured_stdout
        if stdout and stdout.strip():
            display_with_prefix("-----> captured stdout <-----")
            display_with_prefix(stdout, prefix="|")

        stderr = cache2.captured_stderr
        if stderr and stderr.strip():
            display_with_prefix("-----> captured stderr <-----")
            display_with_prefix(stderr, prefix="|")

        if cache2.state == Cache.FAILED:
            display_with_prefix(cache2.exception, prefix="exc |")
            display_with_prefix(cache2.backtrace, prefix="btr |")
        if cache2.result_type_qual:
            print(bold("result type:") + "%s" % cache2.result_type_qual)

    if True:
        job_args = get_job_args(job_id, db=db)
        command, args, kwargs = job_args
        print(bold("command:") + f"{command}")
        print(bold("args:") + f"{args}")
        print(bold("kwargs:") + f"{kwargs}")
