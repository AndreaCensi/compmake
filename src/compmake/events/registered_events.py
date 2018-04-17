# -*- coding: utf-8 -*-
# Warning: this is an auto-generated file
from .structures import EventSpec

compmake_registered_events = {}

__all__ = []


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
add(EventSpec('job-interrupted', ['job_id', 'host', 'bt']))
add(EventSpec('job-now-ready', ['job_id']))
add(EventSpec('manager-phase', ['phase']))
add(EventSpec('manager-loop', ['processing'],
              desc='called each time the manager loops waiting for jobs'
                   'to finish. processing is the list of jobs currently '
                   'processing.'))
# These are called when the manager updates its data structure
add(EventSpec('manager-job-starting', ['job_id']))
add(EventSpec('manager-job-failed', ['job_id']))
add(EventSpec('manager-job-succeeded', ['job_id']))
add(EventSpec('manager-host-failed', ['job_id', 'host', 'reason', 'bt']))
add(EventSpec('manager-init', ['targets', 'more']))
add(EventSpec('manager-wait', ['reasons'],  # dict str -> str
              desc='Reasons why no jobs cannot be instantiated.'))
add(EventSpec('manager-progress', ['targets', 'all_targets', 'done', 'todo',
                                   'failed', 'ready', 'processing', 'deleted',
                                   'blocked']))
add(EventSpec('manager-succeeded', ['nothing_to_do', # there was nothing to do (bool)
                                    'targets', 'all_targets', 'done', 'todo',
                                    'failed', 'ready', 'processing',
                                    'blocked']))
add(EventSpec('manager-interrupted', ['targets', 'all_targets', 'done',
                                      'todo', 'failed', 'ready', 'processing',
                                      'blocked']))
add(EventSpec('manager-failed', ['reason', 'targets', 'all_targets', 'done',
                                 'todo', 'failed', 'ready', 'processing',
                                 'blocked']))
add(EventSpec('worker-status', ['status', 'job_id']))
add(EventSpec('console-starting'))
add(EventSpec('console-ending'))

# These are called for commands strings ("make;clean")
add(EventSpec('command-line-starting', ['command']))
add(EventSpec('command-line-failed', ['command', 'retcode', 'reason']))
add(EventSpec('command-line-succeeded', ['command']))
add(EventSpec('command-line-interrupted', ['command', 'reason']))


# These are called when a single command is executed
add(EventSpec('command-starting', ['command']))
add(EventSpec('command-failed', ['command', 'retcode', 'reason']))
add(EventSpec('command-succeeded', ['command']))
add(EventSpec('command-interrupted', ['command', 'reason']))

add(EventSpec('parmake-status', ['status']))

add(EventSpec('job-defined', ['job_id'], desc='a new job is defined'))
add(EventSpec('job-already-defined', ['job_id']))
add(EventSpec('job-redefined', ['job_id', 'reason']))

add(EventSpec('compmake-bug', ['user_msg', 'dev_msg']))
