from compmake.events import register_handler
from compmake.ui import error
from contracts import indent
from compmake.state import get_compmake_config


# TODO: command-succeeded: {'command': '
# command-interrupted: {'reason': 'KeyboardInterrupt', 'command': 'ls todo'}
def command_interrupted(context, event):  # @UnusedVariable
    error('Command %r interrupted.' % event.kwargs['command'])


register_handler('command-interrupted', command_interrupted)


def command_failed(context, event):  # @UnusedVariable
    error('Command %r failed: %s' % (event.kwargs['command'],
                                     event.kwargs['reason']))


register_handler('command-failed', command_failed)

# my_prefix = '(plugin commands_status) '
my_prefix = ''


def command_line_interrupted(context, event):  # @UnusedVariable
    # Only write something if it is more than one
    command = event.kwargs['command']
    if not ';' in command:
        return
    error(my_prefix + 'Command sequence %r interrupted.' % command)


register_handler('command-line-interrupted', command_line_interrupted)


def command_line_failed(context, event):  # @UnusedVariable
    # Only write something if it is more than one
    command = event.kwargs['command']
    if not ';' in command:
        return
    error(my_prefix + 'Command sequence %r failed.' % command)


register_handler('command-line-failed', command_line_failed)


def job_failed(context, event):  # @UnusedVariable
    job_id = event.kwargs['job_id']
    reason = event.kwargs['reason']
    bt = event.kwargs['bt']

    msg = 'Job %r failed:' % job_id
    s = reason.strip
    if get_compmake_config('echo'):
        s += '\n' + bt

    msg += '\n' + indent(reason.strip(), '| ')
    error(my_prefix + msg)


register_handler('job-failed', job_failed)


def job_interrupted(context, event):  # @UnusedVariable
    error(my_prefix + 'Job %r interrupted:\n %s' %
          (event.kwargs['job_id'],
           indent(event.kwargs['bt'], '> ')))


register_handler('job-interrupted', job_interrupted)


def compmake_bug(context, event):  # @UnusedVariable
    error(my_prefix + event.kwargs['user_msg'])
    error(my_prefix + event.kwargs['dev_msg'])


register_handler('compmake-bug', compmake_bug)


# We ignore some other events; otherwise they will be catched 
# by the default handler
def ignore(context, event):
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

if True:  # debugging
    register_handler('worker-status', ignore)
    register_handler('manager-job-succeeded', ignore)
    register_handler('manager-job-failed', ignore)
    register_handler('manager-job-starting', ignore)

register_handler('manager-succeeded', ignore)  # TODO: maybe write sth


