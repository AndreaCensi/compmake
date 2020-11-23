import itertools
import math
import sys
import time
from collections import namedtuple
from datetime import datetime
from typing import Dict

from compmake import CompmakeGlobalState
from zuper_commons.text import indent
from .tracker import Tracker
from ..events import publish, register_handler
from ..state import get_compmake_config
from ..ui import compmake_colored
from ..ui.visualization import ui_error
from ..utils import get_length_on_screen, getTerminalSize, pad_to_screen_length

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

    console_status_style = get_compmake_config("console_status_style")
    if console_status_style == "normal":

        s_mem = f"mem {cur_mem:2.0f}%"
        if swap > 20:
            s_mem += f" swap {swap:2.0f}%"

        return f"cpu {cpu:2.0f}% {s_mem}"

    else:

        return f"cpu {make_bar(cpu, 7)}"


def make_bar(percent: float, n: int) -> str:
    on = "▉"
    off = "▁"

    ns = int(math.ceil(n * percent / 100))
    ons = on * ns
    offs = off * (n - ns)
    return f"[{ons}{offs}]"


def get_spins():
    # toutf = lambda x: [_.encode('utf8') for _ in x]
    toutf = lambda x: [_ for _ in x]

    # from_sequence = lambda x: toutf(_ for _ in x)

    #     spins = toutf(_ for _ in u"▉▊▋▌▍▎▏▎▍▌▋▊▉")

    def get_spin_fish(n):
        fish_right = ">))'>"
        fish_left = "<'((<"
        s = []
        for i in range(n):
            s.append(" " * i + fish_right)
        for i in range(n):
            s.append(" " * (n - i) + fish_left)
        m = max(len(_) for _ in s)
        # return [_.ljust(m).encode('utf8') for _ in s]

        return [_.ljust(m) for _ in s]

    options = []
    options.append(get_spin_fish(12))
    options.append(list("⣾⣽⣻⢿⡿⣟⣯⣷"))
    options.append(list("◐◓◑◒"))
    options.append(list("◰◳◲◱"))
    options.append(list("◴◷◶◵"))
    #     options.append(from_sequence(u"🕐🕑🕒🕓🕔🕕🕖🕗🕘🕙🕚🕛"))
    options.append(list("▙▛▜▟"))
    #     options.append(['-', '/', '|', '\\'])

    today = datetime.today()
    # change every 3 days
    i = today.day / 3
    i = int(math.ceil(i))
    res = options[i % len(options)]

    return res


spins = get_spins()


def spinner():
    spin_interval = get_compmake_config("console_status_delta") * 0.8
    t = time.time()
    i = t / spin_interval
    i = int(i) % len(spins)
    return spins[i]


def job_counts():
    ss = []

    console_status_style = get_compmake_config("console_status_style")

    styles = {
        "normal": {
            "done": dict(color="green", text="NUM done"),
            "failed": dict(color="red", text="NUM failed"),
            "blocked": dict(text="NUM blocked"),
            "ready": dict(color="yellow", text="NUM ready"),
            "processing": dict(color="blue", text="NUM proc"),
            "todo": dict(color="cyan", text="NUM todo"),
        },
        "compact": {
            "done": dict(color="green", text="NUM ✔"),
            "failed": dict(color="red", text="NUM ✗"),
            "blocked": dict(text="NUM ⌘"),
            "ready": dict(color="yellow", text="NUM ▴‍"),
            "processing": dict(color="blue", text="NUM ⚙"),
            "todo": dict(color="cyan", text="NUM ☯"),
        },
    }
    style = styles[console_status_style]

    values: Dict[str, int] = {
        "done": len(tracker.done),
        "processing": len(tracker.processing),
        "failed": len(tracker.failed),
        "blocked": len(tracker.blocked),
        "ready": len(tracker.ready),
        "todo": len(tracker.todo),
    }

    for k, v in values.items():
        if k not in style:
            continue
        if v > 0:
            sk = style[k]
            text = style[k]["text"].replace("NUM", str(v))
            if "color" in sk:
                text = compmake_colored(text, color=sk["color"])
            ss.append(text)

    return " ".join(ss)


def wait_reasons():
    if tracker.wait_reasons:
        s = "(wait: " + ",".join(tracker.wait_reasons.values()) + ")"
    else:
        s = ""
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
        return "  %d proc." % len(tracker.status)
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
                    if isinstance(frame.iterations[0], int) and isinstance(frame.iterations[1], int):
                        x += ["%s of %s" % (frame.iterations[0] + 1, frame.iterations[1])]
                    else:
                        perc = frame.iterations[0] * 100.0 / frame.iterations[1]
                        x += ["%.1f%%" % perc]

                if level >= 4 and frame.iteration_desc is not None:
                    x += ["(%s)" % frame.iteration_desc]

                if i < len(stack) - 1:
                    x += [">>"]
        X += [" ".join(x)]
    return " ".join(X)


class Tmp:
    last_manager_loop = time.time()


def its_time():
    delta = float(get_compmake_config("console_status_delta"))
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


ShowOption = namedtuple("Option", "length left right weight")


def handle_event(context, event):
    if not get_compmake_config("status_line_enabled"):
        return

    status = system_status()

    options_right = []

    if status:
        options_right.append("%s %s " % (status, job_counts()))
        options_right.append("%s %s %s" % (wait_reasons(), status, job_counts()))

    options_right.append(job_counts())

    sp = spinner()
    options_left = [sp]

    for level in [4, 3, 2, 1, 0, -1, -2, -3]:
        options_left.append(f" compmake {sp} {get_string(level)}")
    #         options_left.append(sp + '  ' + get_string(level))

    cols, _ = getTerminalSize()

    # Make all options together
    options = []
    for l, r in itertools.product(options_left, options_right):
        length = get_length_on_screen(l) + get_length_on_screen(r)
        weight = length
        options.append(ShowOption(length=length, weight=weight, right=r, left=l))

    # sort by length decreasing
    options.sort(key=lambda _: _.length)
    choice = None
    for _ in options:
        if _.length < cols:
            choice = _

    if choice is None:
        # cannot find anything?
        choice = options[0]

    nspaces = cols - get_length_on_screen(choice.right) - get_length_on_screen(choice.left)
    line = choice.left + " " * nspaces + choice.right

    # if get_compmake_config("console_status"):
    #     # if six.PY2:
    #     #     if isinstance(line, unicode):
    #     #         line = line.encode('utf-8')
    #     stream.write(line)
    #
    #     interactive = get_compmake_config("interactive")
    #     if interactive:
    #         stream.write("\r")
    #     else:
    #         stream.write("\n")

    publish(context, "ui-status-summary", string=line)


def manager_host_failed(context, event):
    s = "Host failed for job %s: %s" % (event.job_id, event.reason)
    s += indent(event.bt.strip(), "| ")
    ui_error(context, s)


if get_compmake_config("status_line_enabled"):
    register_handler("manager-loop", handle_event_period)
    register_handler("manager-progress", handle_event_period)
    register_handler("job-progress", handle_event)
    register_handler("job-progress-plus", handle_event)
    register_handler("job-stdout", handle_event)
    register_handler("job-stderr", handle_event)
    register_handler("manager-host-failed", manager_host_failed)
