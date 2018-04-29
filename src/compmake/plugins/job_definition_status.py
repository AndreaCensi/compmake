# -*- coding: utf-8 -*-
import sys

from ..events import register_handler
from ..state import get_compmake_config
from ..ui import compmake_colored
from ..utils import get_screen_columns


stream = sys.stderr

counter = 0


def console_write(s):
    """ Writes a line that will be erased. """
    cols = get_screen_columns()
    s = s.ljust(cols)
    stream.write(s)
    stream.write('\r')


def job_redefined(context, event):  # @UnusedVariable
    if not get_compmake_config('verbose_definition'):
        return
    stream.write(compmake_colored('Redefined %s\r' % event.job_id, 'yellow',
                                  attrs=['bold']))
    stream.write(compmake_colored(event.reason, 'yellow'))
    # stream.write('\n')


def job_defined(context, event):  # @UnusedVariable
    if not get_compmake_config('verbose_definition'):
        return
    global counter
    counter += 1
    console_write('compmake: defining job #%d %s' % (counter, event.job_id))


register_handler('job-redefined', job_redefined)
register_handler('job-defined', job_defined)

# register_handler('job-already-defined', lambda event:
# console_write('Confirming job %s' % event.job_id))



