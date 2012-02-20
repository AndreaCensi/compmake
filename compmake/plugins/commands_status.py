from ..ui import error
from ..events import register_handler


# TODO: command-succeeded: {'command': '

# command-interrupted: {'reason': 'KeyboardInterrupt', 'command': 'ls todo'}
def command_interrupted(event):
    error('Command %r interrupted.' % event.kwargs['command'])
register_handler('command-interrupted', command_interrupted)


def command_failed(event):
    error('Command %r failed: %s' % (event.kwargs['command'],
                                      event.kwargs['reason']))
register_handler('command-failed', command_failed)


def command_line_interrupted(event):
    # Only write something if it is more than one
    command = event.kwargs['command']
    if not ';' in command:
        return
    error('Command sequence %r interrupted.' % command)
register_handler('command-line-interrupted', command_line_interrupted)


def job_interrupted(event):
    # Only write something if it is more than one
    error('Job %r interrupted.' % event.kwargs['job_id'])
register_handler('job_interrupted', job_interrupted)


def command_line_failed(event):
    # Only write something if it is more than one
    command = event.kwargs['command']
    if not ';' in command:
        return
    error('Command sequence %r failed.' % command)
register_handler('command-line-failed', command_line_failed)


#    add(EventSpec('job-failed', ['job_id', 'host', 'reason', 'bt']))
def job_failed(event):
    error('Job %r failed: %s' % (event.kwargs['job_id'],
                                  event.kwargs['reason']))
register_handler('job-failed', job_failed)


def compmake_bug(event):
    error(event.kwargs['user_msg'])
    error(event.kwargs['dev_msg'])

register_handler('compmake-bug', compmake_bug)


# We ignore some other events; otherwise they will be catched 
# by the default handler
def ignore(event):
    pass

register_handler('command-starting', ignore)
register_handler('command-line-starting', ignore)
register_handler('command-line-failed', ignore)
register_handler('command-line-succeeded', ignore)
register_handler('command-line-interrupted', ignore)
register_handler('manager-phase', ignore)

register_handler('parmake-status', ignore)

register_handler('job-succeeded', ignore)
register_handler('job-interrupted', ignore)

if True: # debugging
    register_handler('worker-status', ignore)
    register_handler('manager-job-succeeded', ignore)
    register_handler('manager-job-failed', ignore)
    register_handler('manager-job-starting', ignore)

register_handler('manager-succeeded', ignore) # TODO: maybe write sth


