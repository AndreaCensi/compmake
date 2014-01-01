''' The actual interface of some commands in commands.py '''
from string import rjust
import sys

from ..jobs import (direct_parents, direct_children, get_job_cache, up_to_date,
    parents, children)
from ..structures import Cache
from ..ui import compmake_colored, ui_command, VISUALIZATION


@ui_command(section=VISUALIZATION, alias='lsl')
def details(non_empty_job_list):
    '''Shows the details for the given jobs. '''
    num = 0
    for job_id in non_empty_job_list:
        # insert a separator if there is more than one job
        if num > 0:
            print '-' * 74
        list_job_detail(job_id)
        num += 1


def list_job_detail(job_id):
    # computation = get_computation(job_id)
    cache = get_job_cache(job_id)
    dparents = direct_parents(job_id)
    all_parents = parents(job_id)
    other_parents = set(all_parents) - set(dparents)
    dchildren = direct_children(job_id)
    all_children = children(job_id)
    other_children = set(all_children) - set(dchildren)
    up, reason = up_to_date(job_id)

    red = lambda x: compmake_colored(x, 'red')
    bold = lambda x: compmake_colored(rjust(x + ' ', 15), attrs=['bold'])

    try:
        def format_list(x):
            return '\n- '.join([''] + sorted(x))
        
        # TODO: make it work in Python3K
        print(bold('Job ID:') + '%s' % job_id)
        print(bold('Status:') + '%s' % Cache.state2desc[cache.state])
        print(bold('Uptodate:') + '%s (%s)' % (up, reason))
        print(bold('Dependences: (direct)') + ' (%d) ' % len(dchildren) + format_list(dchildren))
        print(bold('Dependences: (other)') + ' (%d) ' % len(other_children) + format_list(other_children))
        print(bold('Jobs depending on this (direct):') + format_list(dparents))
        print(bold('Jobs depending on this (other levels):') + format_list(other_parents))
        
        if cache.state == Cache.DONE and cache.done_iterations > 1:
            print(bold('Iterations:') + '%s' % cache.done_iterations)
            print(bold('Wall Time:') + '%.4f s' % cache.walltime_used)
            print(bold('CPU Time:') + '%.4f s' % cache.cputime_used)
            print(bold('Host:') + '%s' % cache.host)

        if cache.state == Cache.IN_PROGRESS:
            print(bold('Progress:') + '%s/%s' % \
                (cache.iterations_in_progress, cache.iterations_goal))

        if cache.state == Cache.FAILED:
            print(red(cache.exception))
            print(red(cache.backtrace))

        def display_with_prefix(buffer, prefix,  # @ReservedAssignment
                                transform=lambda x: x, out=sys.stdout):
            for line in buffer.split('\n'):
                out.write('%s%s\n' % (prefix, transform(line)))

        if cache.captured_stdout:
            print("-----> captured stdout <-----")
            display_with_prefix(cache.captured_stdout, prefix='|',
                                transform=lambda x: x)

        if cache.captured_stderr:
            print("-----> captured stderr <-----")
            display_with_prefix(cache.captured_stdout, prefix='|',
                                transform=lambda x: x)




    except AttributeError:
        pass

