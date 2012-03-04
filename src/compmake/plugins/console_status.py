from .. import CompmakeGlobalState
from ..events import register_handler
from ..utils import (pad_to_screen_length, get_length_on_screen, colored,
    getTerminalSize)
from .tracker import Tracker
import sys
import time


stream = sys.stderr

tracker = Tracker()


def system_status():
    stats = CompmakeGlobalState.system_stats
    if not stats.available(): # psutil not installed
        # TODO: use os.load 
        return ""

    cpu = stats.avg_cpu_percent()
    cur_mem = stats.cur_phymem_usage_percent()

    return  ('cpu %2.0f%% mem %2.0f%% ' % (cpu, cur_mem))


def spinner():
    spins = ['-', '/', '|', '\\']
    return spins[tracker.nloops % len(spins)]


def job_counts():
    done_style = dict(color='green')
    failed_style = dict(color='red')
    blocked_style = dict()
    ready_style = dict(color='yellow')
    proc_style = dict(color='yellow')
    s = ""
    s += colored("%d done" % len(tracker.done), **done_style)

    if tracker.processing:
        s += colored(" %d proc" % len(tracker.processing), **proc_style)

    if tracker.failed:
        s += colored(" %d failed" % len(tracker.failed), **failed_style)

    if tracker.blocked:
        s += colored(" %d blocked" % len(tracker.blocked), **blocked_style)

    s += colored(" %d todo" % len(tracker.todo), **ready_style)

    if tracker.ready:
        s += colored(" (%d ready)" % len(tracker.ready), **ready_style)

    #s = 'status: %s proc: %s' % (tracker.status.keys(), tracker.processing)
    return s


def current_slot(intervals):
    period = sum(intervals)
    index = int(time.time()) % period
    csum = 0
    for i, delta in enumerate(intervals):
        if (index >= csum) and (index < csum + delta):
            return i
        csum += delta
    return len(intervals) - 1


def display_rotating(strings, intervals):
    ''' Rotates the display of the given strings. 
        For now, we assume intervals to be round integers.
    '''
    which = current_slot(intervals)
    L = max(get_length_on_screen(x) for x in strings)
    aligned = pad_to_screen_length(strings[which], L)
    return  aligned


def handle_event(event):  # @UnusedVariable
    s = ""
    s += spinner() + ' '

    status = system_status()

    if status: # available 
        s += display_rotating([system_status(),
                               job_counts()], [2, 5])
    else:
        s += job_counts()

    def get_string(level):
        if level == -2:
            return
        if level == -1:
            return '  %d proc.' % len(tracker.status)
        X = []

        for job_id, status in tracker.status.items():
            x = []
            if level >= 1:
                x += [job_id]
                # + ':'

            if level <= 1 or not job_id in tracker.status_plus:
                x += [status]
            elif job_id in tracker.status_plus:
                x += []
                stack = tracker.status_plus[job_id]
                for i, frame in enumerate(stack):
                    if level >= 3:
                        x += [frame.name]

                    if level >= 2:
                        x += ["%s/%s" % (frame.iterations[0] + 1,
                                         frame.iterations[1])]

                    if level >= 4 and frame.iteration_desc is not None:
                        x += ["(" + frame.iteration_desc + ")"]

                    if i < len(stack) - 1:
                        x += ['>>']
#            X += ["[" + " ".join(x) + "]"]
            X += [" ".join(x)]
        return " | " + " ".join(X)

    cols, _ = getTerminalSize()

    for level in [4, 3, 2, 1, 0, -1, -2]:
        x = s + get_string(level)
        if get_length_on_screen(x) <= cols:
            choice = x
            break
    else:
        # everything is too long
        # TODO: warn
        choice = s

    choice = pad_to_screen_length(choice, cols, align_right=True)
    stream.write(choice)
    stream.write('\r')


register_handler('manager-loop', handle_event)
register_handler('manager-progress', handle_event)
register_handler('job-progress', handle_event)
register_handler('job-progress-plus', handle_event)
register_handler('job-stdout', handle_event)
register_handler('job-stderr', handle_event)


