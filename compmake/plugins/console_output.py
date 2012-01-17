from ..events import register_handler
import sys
from compmake.utils.capture import pad_to_screen
from compmake.utils.visualization import error, colored, get_screen_columns

# sys.stdout will be changed later
stream = sys.stdout


class Storage:
    max_len = 0
    last_job_id = None


def handle_event(event, is_stderr):
    job_id = event.kwargs['job_id']
    lines = event.kwargs['lines']

    Storage.max_len = max(Storage.max_len, len(job_id))

    for line in lines:

        formats = '%%%ds' % Storage.max_len

        prefix = formats % job_id
        prefix_empty = formats % ''

        if Storage.last_job_id != job_id:
            Storage.last_job_id = job_id
            #prefix = colored(prefix, color='cyan', attrs=['dark'])
            prefix = colored(prefix, color='cyan')
        else:
            prefix = prefix_empty

        if is_stderr:
            sep = colored('|', 'red')
        else:
            sep = colored('|', 'cyan')

        # Now let's take lines that do not fit the length
        if True:
            max_space = (get_screen_columns() - 1
                         - len('%s%s%s' % (prefix, sep, '')))

            sublines = clip_to_screen(line, max_space)

            for a, subline in enumerate(sublines):
                if a == 0:
                    screen_line = '%s%s%s' % (prefix, sep, subline)
                else:
                    screen_line = '%s%s%s' % (prefix_empty, ' ', subline)

                screen_line = pad_to_screen(screen_line)
                stream.write(screen_line)
                stream.write('\n')
        else:
            screen_line = '%s%s%s' % (prefix, sep, line)

            screen_line = pad_to_screen(screen_line)
            stream.write(screen_line)
            stream.write('\n')


# XXX: this might have problems with colored versions
def clip_to_screen(line, max_len):
    sublines = []
    while len(line):
        clip = min(len(line), max_len)
        subline = line[:clip]
        sublines.append(subline)
        line = line[clip:]
    return sublines


def handle_event_stdout(event):
    handle_event(event, False)


def handle_event_stderr(event):
    handle_event(event, True)


register_handler('job-stdout', handle_event_stdout)
register_handler('job-stderr', handle_event_stderr)


def handle_job_failed(event):
    job_id = event.kwargs['job_id']
    host = event.kwargs['host']
    reason = event.kwargs['reason']
    bt = event.kwargs['bt']

    error('Job %r failed on host %r: %s\n%s' %
          (job_id, host, reason, bt))

register_handler('job-failed', handle_job_failed)


