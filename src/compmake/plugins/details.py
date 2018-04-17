# -*- coding: utf-8 -*-
""" The actual interface of some commands in commands.py """
import sys

from ..jobs import (children, direct_children, direct_parents, get_job,
                    get_job_args, get_job_cache, job_args_sizeof,
                    job_cache_exists,
                    job_cache_sizeof, job_userobject_exists,
                    job_userobject_sizeof, parents)
from ..structures import Cache
from ..ui import VISUALIZATION, compmake_colored, ui_command


@ui_command(section=VISUALIZATION, alias='lsl')
def details(non_empty_job_list, context, cq, max_lines=None):
    """ Shows the details for the given jobs including
        dependencies and stderr/stdout.

        The stderr/stdout lines are truncated. Use the ``max_lines``
        argument to see more:

            details max_lines=1000
    """
    num = 0
    for job_id in non_empty_job_list:
        # insert a separator if there is more than one job
        if num > 0:
            print('-' * 74)
        list_job_detail(job_id, context, cq, max_lines=max_lines)
        num += 1


def list_job_detail(job_id, context, cq, max_lines):
    db = context.get_compmake_db()

    dparents = direct_parents(job_id, db=db)
    all_parents = parents(job_id, db=db)
    other_parents = set(all_parents) - set(dparents)
    
    
    # TODO: use quicker up to date
    up, reason, _ = cq.up_to_date(job_id)

    red = lambda x: compmake_colored(x, 'red')
    bold = lambda x: compmake_colored((x + ' ').rjust(15), attrs=['bold'])

    def format_list(x):
        return '\n- '.join([''] + sorted(x))

    job = get_job(job_id, db=db)

    # TODO: make it work in Python3K
    print(bold('Job ID:') + '%s' % job_id)
    print(bold('Defined by:') + '%s' % job.defined_by)

    job_args = get_job_args(job_id, db=db)
    command, args, kwargs = job_args  # @UnusedVariable
    print(bold('command:') + '%s' % command)

    dchildren = direct_children(job_id, db=db)
    print(
        bold('Dependencies: (direct)') + ' (%d) ' % len(
            dchildren) + format_list(dchildren))
    
    all_children = children(job_id, db=db)
    other_children = set(all_children) - set(dchildren)
    print(bold('Dependencies: (other)') + ' (%d) ' % len(
        other_children) + format_list(other_children))
    
    print(bold('Dependencies: (dynamic)') + '%s' % job.dynamic_children)
    
    print(bold('Depending on this (direct):') + format_list(dparents))
    print(bold('Depending on this (other):') + format_list(
        other_parents))

    if job_cache_exists(job_id, db=db):
        cache2 = get_job_cache(job_id, db=db)

        print(bold('Status:') + '%s' % Cache.state2desc[cache2.state])
        print(bold('Uptodate:') + '%s (%s)' % (up, reason))

        if cache2.state == Cache.DONE:  # and cache.done_iterations > 1:
            # print(bold('Iterations:') + '%s' % cache.done_iterations)
            print(bold('Wall Time:') + '%.4f s' % cache2.walltime_used)
            print(bold('CPU Time:') + '%.4f s' % cache2.cputime_used)

            print('making: %s' % cache2.int_make)
            print('-- load: %s' % cache2.int_load_results)
            print('-- comp: %s' % cache2.int_compute)
            print('--   GC: %s' % cache2.int_gc)
            print('-- save: %s' % cache2.int_save_results)

            print(bold('Host:') + '%s' % cache2.host)

            if not job_userobject_exists(job_id, db):
                print(red('inconsistent DB: user object does not exist.'))
    else:
        print(bold('Status:') + '%s' % Cache.state2desc[Cache.NOT_STARTED])
        cache2 = None

    jobargs_size = job_args_sizeof(job_id, db)
    print(bold('      args size: ') + '%s' % jobargs_size)

    if job_cache_exists(job_id, db):
        cache_size = job_cache_sizeof(job_id, db)
        print(bold('     cache size: ') + '%s' % cache_size)
    else:
        cache_size = 0

    if job_userobject_exists(job_id, db):
        userobject_size = job_userobject_sizeof(job_id, db)
        print(bold('userobject size: ') + '%s' % userobject_size)
    else:
        userobject_size = 0

    total = jobargs_size + cache_size + userobject_size
    print(bold('          Total: ') + '%s' % total)

    def display_with_prefix(buffer, prefix,  # @ReservedAssignment
                            transform=lambda x: x, out=sys.stdout):
        lines = buffer.split('\n')
        if max_lines is not None:
            if len(lines) > max_lines:
                warn = '.... Showing only last %d lines of %d ... ' % (
                    max_lines, len(lines))
                lines = [warn] + lines[-max_lines:]

        for line in lines:
            out.write('%s%s\n' % (prefix, transform(line)))

    if cache2 is not None:
        stdout = cache2.captured_stdout
        if stdout and stdout.strip():
            print("-----> captured stdout <-----")
            display_with_prefix(stdout, prefix='|', transform=lambda x: x)

        stderr = cache2.captured_stderr
        if stderr and stderr.strip():
            print("-----> captured stderr <-----")
            display_with_prefix(stderr, prefix='|', transform=lambda x: x)

        if cache2.state == Cache.FAILED:
            print(red(cache2.exception))
            print(red(cache2.backtrace))
