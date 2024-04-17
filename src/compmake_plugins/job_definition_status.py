import sys

from compmake import Context, Event, compmake_colored, register_handler
from compmake_utils import get_screen_columns

stream = sys.stderr

counter = 0


def console_write(s):
    """Writes a line that will be erased."""
    cols = get_screen_columns()
    s = s.ljust(cols)
    stream.write(s)
    stream.write("\r")


async def job_redefined(context: Context, event: Event):
    if not context.get_compmake_config("verbose_definition"):
        return
    stream.write(compmake_colored("Redefined %s\r" % event.kwargs["job_id"], "yellow", attrs=["bold"]))
    stream.write(compmake_colored(event.kwargs["reason"], "yellow"))
    # stream.write('\n')


async def job_defined(context: Context, event: Event):
    if not context.get_compmake_config("verbose_definition"):
        return
    global counter
    counter += 1
    console_write("compmake: defining job #%d %s" % (counter, event.kwargs["job_id"]))


register_handler("job-redefined", job_redefined)
register_handler("job-defined", job_defined)

# register_handler('job-already-defined', lambda event:
# console_write('Confirming job %s' % event.job_id))
