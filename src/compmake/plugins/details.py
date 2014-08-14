''' The actual interface of some commands in commands.py '''
import sys

from ..jobs import (direct_parents, direct_children, get_job_cache, parents,
    children, CacheQueryDB, get_job)
from ..structures import Cache
from ..ui import compmake_colored, ui_command, VISUALIZATION
import string


@ui_command(section=VISUALIZATION, alias='lsl')
def details(non_empty_job_list,  context, max_lines=None):
    '''Shows the details for the given jobs. '''
    num = 0
    db = context.get_compmake_db()
    cq = CacheQueryDB(db=db)
    for job_id in non_empty_job_list:
        # insert a separator if there is more than one job
        if num > 0:
            print('-' * 74)
        list_job_detail(job_id, context, cq, max_lines=max_lines)
        num += 1


def list_job_detail(job_id, context, cq, max_lines):
    db = context.get_compmake_db()
    cache = get_job_cache(job_id, db=db)
    dparents = direct_parents(job_id, db=db)
    all_parents = parents(job_id, db=db)
    other_parents = set(all_parents) - set(dparents)
    dchildren = direct_children(job_id, db=db)
    all_children = children(job_id, db=db)
    other_children = set(all_children) - set(dchildren)
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
    print(bold('Status:') + '%s' % Cache.state2desc[cache.state])
    print(bold('Uptodate:') + '%s (%s)' % (up, reason))
    print(bold('Dependences: (direct)') + ' (%d) ' % len(dchildren) + format_list(dchildren))
    print(bold('Dependences: (other)') + ' (%d) ' % len(other_children) + format_list(other_children))
    print(bold('Jobs depending on this (direct):') + format_list(dparents))
    print(bold('Jobs depending on this (other levels):') + format_list(other_parents))

    if cache.state == Cache.DONE:  # and cache.done_iterations > 1:
        # print(bold('Iterations:') + '%s' % cache.done_iterations)
        print(bold('Wall Time:') + '%.4f s' % cache.walltime_used)
        print(bold('CPU Time:') + '%.4f s' % cache.cputime_used)
        print(bold('Host:') + '%s' % cache.host)

    #         if cache.state == Cache.IN_PROGRESS:
    #             print(bold('Progress:') + '%s/%s' % \
    #                 (cache.iterations_in_progress, cache.iterations_goal))

 
        
    def display_with_prefix(buffer, prefix,  # @ReservedAssignment
                            transform=lambda x: x, out=sys.stdout):
        lines = buffer.split('\n')
        if max_lines is not None:
            if len(lines) > max_lines:
                warn ='.... Showing only last %d lines of %d ... ' % (max_lines, len(lines))
                lines = [warn] +lines[-max_lines:]
                
            
        for line in lines:
            out.write('%s%s\n' % (prefix, transform(line)))


    
    stdout = cache.captured_stdout
    if stdout and stdout.strip():
        print("-----> captured stdout <-----")
        display_with_prefix(stdout, prefix='|', transform=lambda x: x)

    stderr = cache.captured_stderr
    if stderr and stderr.strip():
        print("-----> captured stderr <-----")
        display_with_prefix(stderr, prefix='|', transform=lambda x: x)

    if cache.state == Cache.FAILED:
        print(red(cache.exception))
        print(red(cache.backtrace))
