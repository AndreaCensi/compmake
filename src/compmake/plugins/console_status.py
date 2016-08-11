from ..events import register_handler
from ..state import get_compmake_config
from ..ui import compmake_colored, error
from ..utils import getTerminalSize, get_length_on_screen, pad_to_screen_length
from .tracker import Tracker
from compmake import CompmakeGlobalState
from contracts import indent
import sys
import time


stream = sys.stderr

tracker = Tracker()


def system_status():
    stats = CompmakeGlobalState.system_stats
    if not stats.available():  # psutil not installed
        # TODO: use os.load 
        return ""

    cpu = stats.avg_cpu_percent()
    cur_mem = stats.cur_phymem_usage_percent()
    swap = stats.cur_virtmem_usage_percent()

    s_mem = 'mem %2.0f%%' % cur_mem
    if swap > 20:
        s_mem += ' swap %2.0f%%' % swap

    return 'cpu %2.0f%% %s' % (cpu, s_mem)


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
    if tracker.done:
        s += compmake_colored("%d done" % len(tracker.done), 
                              **done_style)

    if tracker.processing:
        s += compmake_colored(" %d proc" % len(tracker.processing),
                              **proc_style)

    if tracker.failed:
        s += compmake_colored(" %d failed" % len(tracker.failed),
                              **failed_style)

    if tracker.blocked:
        s += compmake_colored(" %d blocked" % len(tracker.blocked),
                              **blocked_style)

    if tracker.ready:
        s += compmake_colored(" %d ready" % len(tracker.ready),
                              **ready_style)

    if tracker.todo:
        s += compmake_colored(" %d waiting" % len(tracker.todo), 
                              **ready_style)
    
    return s


def wait_reasons():
    # s += "(" + ",".join(["%s:%s" % (k, v)
    #                         for (k, v) in  tracker.wait_reasons.items()])
    # + ')'
    if tracker.wait_reasons:
        s = "(wait: " + ",".join(tracker.wait_reasons.values()) + ')'
    else:
        s = ""
    # s = 'status: %s proc: %s' % (tracker.status.keys(), tracker.processing)
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


def display_rotating(strings, intervals, align_right=False):
    """ Rotates the display of the given strings.
        For now, we assume intervals to be round integers.
    """
    which = current_slot(intervals)
    L = max(get_length_on_screen(x) for x in strings)
    aligned = pad_to_screen_length(strings[which], L, align_right=align_right)
    return aligned


def get_string(level):
    if level == -3:
        return ""
    if level == -2:
        return "..."
    if level == -1:
        return '  %d proc.' % len(tracker.status)
    X = []

    for job_id, status in tracker.status.items():
        x = []
        if level >= 1:
            x += [job_id]

        if level <= 1 or not job_id in tracker.status_plus:
            x += [status]
        elif job_id in tracker.status_plus:
            x += []
            stack = tracker.status_plus[job_id]
            for i, frame in enumerate(stack):
                if level >= 3:
                    x += [frame.name]

                if level >= 2:
                    # XXX: this is never used somehow, see tracker
                    # that's where the code is executed to display iterations
                    if (isinstance(frame.iterations[0], int)
                        and isinstance(frame.iterations[1], int)):
                        x += ["%s of %s" % (frame.iterations[0] + 1,
                                            frame.iterations[1])]
                    else:
                        perc = frame.iterations[0] * 100.0 / frame.iterations[
                            1]
                        x += ['%.1f%%' % perc]

                if level >= 4 and frame.iteration_desc is not None:
                    x += ["(%s)" % str(frame.iteration_desc)]

                if i < len(stack) - 1:
                    x += ['>>']
        X += [" ".join(x)]
    return " ".join(X)


class Tmp():
    last_manager_loop = time.time()


def its_time():
    delta = 0.33
    t = time.time()
    dt = t - Tmp.last_manager_loop
    if dt > delta:
        Tmp.last_manager_loop = t
        return True
    else:
        return False


def handle_event_period(context, event):
    if its_time():
        handle_event(context, event)


def handle_event(context, event):  # @UnusedVariable
    if not get_compmake_config('status_line_enabled'):
        return

    text_right = ' '

    status = system_status()

    if status:  # available
        if False:
            if True:  # TODO: add configuration 
                options = [wait_reasons() + " " + status, job_counts()]
            else:
                options = [status, job_counts()]
            text_right += display_rotating(options, [3, 5], align_right=True)
        else:
            text_right += wait_reasons() + ' ' + status + ' ' + job_counts()
    else:
        text_right += job_counts()

    cols, _ = getTerminalSize()

    remaining = cols - get_length_on_screen(text_right)

    options_left = [spinner() + '  ' + get_string(level)
                    for level in [4, 3, 2, 1, 0, -1, -2, -3]]

    for x in options_left:
        if get_length_on_screen(x) <= remaining:
            text_left = x
            break
    else:
        text_left = ''

    nspaces = (cols
               - get_length_on_screen(text_right)
               - get_length_on_screen(text_left))
    line = text_left + ' ' * nspaces + text_right

    # line = pad_to_screen_length(choice, remaining, align_right=True) + s

    if get_compmake_config('console_status'):
        stream.write(line)
    
        interactive = get_compmake_config('interactive')
        if interactive:
            stream.write('\r')
        else:
            stream.write('\n')


def manager_host_failed(context, event):  # @UnusedVariable
    s = 'Host failed for job %s: %s' % (event.job_id, event.reason)
    s += indent(event.bt.strip(), '| ')
    error(s)
    

if get_compmake_config('status_line_enabled'):
    register_handler('manager-loop', handle_event_period)
    register_handler('manager-progress', handle_event_period)
    register_handler('job-progress', handle_event)
    register_handler('job-progress-plus', handle_event)
    register_handler('job-stdout', handle_event)
    register_handler('job-stderr', handle_event)
    register_handler('manager-host-failed', manager_host_failed)
