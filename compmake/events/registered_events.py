# Warning: this is an auto-generated file
from . import EventSpec

compmake_registered_events = {}


def add(e):
    compmake_registered_events[e.name] = e


add(EventSpec('compmake-init'))
add(EventSpec('compmake-closing'))
add(EventSpec('job-stdout', ['job_id', 'host', 'lines']))
add(EventSpec('job-stderr', ['job_id', 'host', 'lines']))
add(EventSpec('job-progress', ['job_id', 'host', 'done', 'progress', 'goal']))
add(EventSpec('job-progress-plus', ['job_id', 'host', 'stack']))
add(EventSpec('job-succeeded', ['job_id', 'host']))
add(EventSpec('job-failed', ['job_id', 'host', 'reason', 'bt']))
add(EventSpec('job-instanced', ['job_id', 'host']))
add(EventSpec('job-starting', ['job_id', 'host']))
add(EventSpec('job-finished', ['job_id', 'host']))
add(EventSpec('job-interrupted', ['job_id', 'host', 'reason']))
add(EventSpec('job-now-ready', ['job_id']))
add(EventSpec('manager-init', ['targets', 'more']))
add(EventSpec('manager-progress', ['targets', 'all_targets', 'done', 'todo',
                                    'failed', 'ready', 'processing']))
add(EventSpec('manager-succeeded', ['targets', 'all_targets', 'done', 'todo',
                                     'failed', 'ready', 'processing']))
add(EventSpec('manager-interrupted', ['targets', 'all_targets', 'done',
                                    'todo', 'failed', 'ready', 'processing']))
add(EventSpec('manager-failed', ['reason', 'targets', 'all_targets', 'done',
                                  'todo', 'failed', 'ready', 'processing']))
add(EventSpec('worker-status', ['status', 'job_id']))
add(EventSpec('console-starting'))
add(EventSpec('console-ending'))
add(EventSpec('command-starting', ['command']))
add(EventSpec('command-failed', ['command', 'retcode', 'reason']))
add(EventSpec('command-succeeded', ['command']))
add(EventSpec('command-interrupted', ['command', 'reason']))
add(EventSpec('job-defined', ['job_id'],
              desc='a new job is defined'))
add(EventSpec('job-already-defined', ['job_id']))
add(EventSpec('job-redefined', ['job_id', 'reason']))
