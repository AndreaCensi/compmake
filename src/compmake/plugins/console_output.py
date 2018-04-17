# -*- coding: utf-8 -*-
import sys

from .. import get_compmake_config
from ..events import register_handler
from ..ui import compmake_colored
from ..utils import (get_length_on_screen, get_screen_columns, pad_to_screen,
                     pad_to_screen_length)


# sys.stdout will be changed later
stream = sys.stdout


class Storage():
    max_len = 0
    last_job_id = None


def plot_with_prefix(job_id, lines, is_stderr):

    for line in lines:

        formats = '%%%ds' % Storage.max_len

        prefix = formats % job_id
        prefix_empty = formats % ''

        if Storage.last_job_id != job_id:
            Storage.last_job_id = job_id
            # prefix = colored(prefix, color='cyan', attrs=['dark'])
            prefix = compmake_colored(prefix, color='cyan')
        else:
            prefix = prefix_empty

        if is_stderr:
            sep = compmake_colored('|', 'red')
        else:
            sep = compmake_colored('|', 'cyan')

        # Now let's take lines that do not fit the length
        if True:  # second
            # This has problems with escape characters
            # (in addition to get_screen_columns() not functioning sometime.)

            split_lines = False
            if split_lines:
                max_space = (get_screen_columns() - 1
                             - get_length_on_screen('%s%s%s' % (prefix, sep, '')))

                sublines = clip_to_length(line, max_space)

                for a, subline in enumerate(sublines):
                    if a == 0:
                        screen_line = '%s%s%s' % (prefix, sep, subline)
                    else:
                        screen_line = '%s%s%s' % (prefix_empty, ' ', subline)

                    screen_line = pad_to_screen(screen_line)
                    stream.write(screen_line)
                    stream.write('\n')
            else:
                stream.write(line)
                stream.write('\n')
        else:
            screen_line = '%s%s%s' % (prefix, sep, line)

            screen_line = pad_to_screen(screen_line)
            stream.write(screen_line)
            stream.write('\n')


def write_screen_line(s):
    """ Writes and pads """
    # TODO: check that it is not too long
    s = pad_to_screen(s)
    stream.write(s)
    stream.write('\n')
    stream.flush()


def plot_normally(job_id, lines, is_stderr):  # @UnusedVariable
    for line in lines:
        if Storage.last_job_id != job_id:
            Storage.last_job_id = job_id
            # job_name = colored('%s' % job_id, color='cyan')
            header = pad_to_screen('___ %s ' % job_id, pad='_')
            header = compmake_colored(header, color='cyan')
            write_screen_line(header)

        max_size = get_screen_columns()
        # if debug_padding:
        # prefix = compmake_colored('>', color='red')
        # postfix = compmake_colored('<', color='blue')
        # else:
        prefix = ""
        postfix = ""
        
        # reproducing 3.5.6: safe
        # write_screen_line(line)
        
        if True:  # need to check unicode anyway
            # 3.5.10 -- most recent
            
            sublines = break_lines(prefix, line, postfix, max_size)

            for s in sublines:
                write_screen_line(s)
            
        elif False:
            sublines = break_lines_and_pad(prefix, line, postfix, max_size)
            for s in sublines:
                write_screen_line(s)
        else:
            # 3.5.6
            write_screen_line(line)

def break_lines(prefix, line, postfix, max_size):
    # Now let's take lines that do not fit the length
    prefix_len = get_length_on_screen(prefix)
    postfix_len = get_length_on_screen(postfix)

    max_space = (max_size - postfix_len - prefix_len)
    
    if max_space < 10:
        msg = 'Weird max space: %s' % max_space
        msg += ' max_size: %s prefix: %s postfix: %s' % (max_size, prefix_len, postfix_len)
        raise ValueError(msg)

    # XXX: might have problems with colors
    sublines = clip_to_length(line, max_space)

    lines = []
    for _, subline in enumerate(sublines):
        # pad = '+' if debug_padding else ' '
#         pad = ' '
#         subline = pad_to_screen_length(subline, max_space, pad=pad)
        line = '%s%s%s' % (prefix, subline, postfix)
        lines.append(line)
    return lines


# @contract(prefix='str', line='str', postfix='str', returns='list[>=1]x(str)')
def break_lines_and_pad(prefix, line, postfix, max_size):
    # Now let's take lines that do not fit the length
    prefix_len = get_length_on_screen(prefix)
    postfix_len = get_length_on_screen(postfix)

    max_space = (max_size - postfix_len - prefix_len)

    # XXX: might have problems with colors
    sublines = clip_to_length(line, max_space)

    lines = []
    for _, subline in enumerate(sublines):
        # pad = '+' if debug_padding else ' '
        pad = ' '
        subline = pad_to_screen_length(subline, max_space, pad=pad)
        line = '%s%s%s' % (prefix, subline, postfix)
        lines.append(line)
    return lines


def handle_event(event, is_stderr):
    job_id = event.kwargs['job_id']
    lines = event.kwargs['lines']

    Storage.max_len = max(Storage.max_len, len(job_id))

    if Storage.max_len < 15:
        plot_with_prefix(job_id, lines, is_stderr)
    else:
        plot_normally(job_id, lines, is_stderr)


# XXX: this might have problems with colored versions
def clip_to_length(line, max_len):
    if max_len <= 0:
        msg = 'Max length should be positive.'
        raise ValueError(msg)
    sublines = []
    while len(line):
        clip = min(len(line), max_len)
        subline = line[:clip]
        sublines.append(subline)
        line = line[clip:]
    return sublines


def handle_event_stdout(event, context):  # @UnusedVariable
    if get_compmake_config('echo_stdout'):
        handle_event(event, False)


def handle_event_stderr(event, context):  # @UnusedVariable
    if get_compmake_config('echo_stderr'):
        handle_event(event, True)


register_handler('job-stdout', handle_event_stdout)
register_handler('job-stderr', handle_event_stderr)
