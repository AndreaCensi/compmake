''' The actual interface of some commands in commands.py '''
from ..jobs import direct_parents, direct_children, get_job_cache, up_to_date
from ..structures import Cache
from ..ui import ui_command, VISUALIZATION
from string import rjust
import sys
from compmake.ui.visualization import compmake_colored


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
    parents = direct_parents(job_id)
    children = direct_children(job_id)
    up, reason = up_to_date(job_id)

    red = lambda x: compmake_colored(x, 'red')
    bold = lambda x: compmake_colored(rjust(x + ' ', 15), attrs=['bold'])

    try:
        # TODO: make it work in Python3K
        print(bold('Job ID:') + '%s' % job_id)
        print(bold('Status:') + '%s' % Cache.state2desc[cache.state])
        print(bold('Uptodate:') + '%s (%s)' % (up, reason))
        print(bold('Children:') + '%s' % ', '.join(children))
        print(bold('Parents:') + '%s' % ', '.join(parents))

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

