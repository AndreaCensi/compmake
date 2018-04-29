# -*- coding: utf-8 -*-
""" This plugin dumps all events received. """
import sys

from ..events import register_fallback_handler, register_handler
from ..ui import compmake_colored
from ..utils import pad_to_screen


# We save it, because it will be redirected during job execution
stream = sys.stderr
other_stream = sys.stdout


def print_event(context, event):  # @UnusedVariable
    other_stream.flush()

    # age = time.time() - event.timestamp
    #    if age > 0.5:
    #        ages = '%.3fs ago' % age
    #    else:
    #        ages = ""

    s = str(event.kwargs)
    #    print ('%r has len %d' % (s, len(s)))
    MAX_LEN = 1000  # TODO: 
    # TODO: clip_to_length(s, ' [...]')
    if len(s) > MAX_LEN:
        suff = ' [...]'
        s = s[:MAX_LEN - len(suff)] + suff
    #        s = s[:MAX_LEN]

    msg = '%s: %s' % (event.name, s)
    msg = compmake_colored(pad_to_screen(msg), 'yellow')
    stream.write(msg)
    stream.write('\n')
    stream.flush()


if False:
    register_handler("*", print_event)
else:
    register_fallback_handler(print_event)
