# -*- coding: utf-8 -*-
import time

from contracts import contract, describe_type

from ..structures import ProgressStage


class Globals():
    stack = []
    callbacks = []


def progress_stack_updated():
    for callback in Globals.callbacks:
        callback(Globals.stack)


def init_progress_tracking(my_callback):
    Globals.stack = []
    Globals.callbacks = []  # OK, otherwise old callbacks will update status
    Globals.callbacks.append(my_callback)
    progress_stack_updated()


@contract(taskname='str', iterations='tuple(int|float,int|float)')
def progress(taskname, iterations, iteration_desc=None):
    """
        Function used by the user to describe the state of the computation.

       Parameters
       ---------

       - ``name``: must be a string, describing the current task.

       - ``iterations``: must be a tuple of two integers (k,N), meaning
          that the current iteration is the k-th out of N.

       - ``iteration_desc``: an optional string describing the current i
          teration

       Example: ::

            for i in range(n):
                progress('Reading files', (i,n),
                         'processing file %s' % file[i])
    """

    if not isinstance(taskname, str):
        raise ValueError('The first argument to progress() is the task name ' +
                         'and must be a string; you passed a %s.' %
                         describe_type(taskname))

    if not isinstance(iterations, tuple):
        raise ValueError('The second argument to progress() must be a tuple,' +
                         ' you passed a %s.' % describe_type(iterations))
    if not len(iterations) == 2:
        raise ValueError('The second argument to progress() must be a tuple ' +
                         ' of length 2, not of length %s.' % len(iterations))

    if not isinstance(iterations[0], (int, float)):
        raise ValueError('The first element of the tuple passed to progress ' +
                         'must be integer or float, not a %s.' %
                         describe_type(iterations[0]))

    if not iterations[1] is None and not isinstance(iterations[1],
                                                    (int, float)):
        raise ValueError('The second element of the tuple passed to progress '
                         'must be either None or an integer, not a %s.' %
                         describe_type(iterations[1]))

    if iterations[1] < iterations[0]:
        raise ValueError('Invalid iteration tuple: %s' % str(iterations))

    BROADCAST_INTERVAL = 0.5

    is_last = iterations[0] == iterations[1] - 1

    stack = Globals.stack

    for i, stage in enumerate(stack):
        if stage.name == taskname:
            # remove children
            has_children = i < len(stack) - 1
            stack[i + 1:] = []
            stage.iterations = iterations
            stage.iteration_desc = iteration_desc
            # TODO: only send every once in a while
            if ((is_last or has_children) or
                    (stage.last_broadcast is None) or
                    (time.time() - stage.last_broadcast > BROADCAST_INTERVAL)):
                progress_stack_updated()
                stage.last_broadcast = time.time()
            if stage.last_broadcast is None:
                stage.last_broadcast = time.time()
            break
    else:
        # If we are here, we haven't found taskname in the stack.
        # This means that it is either a child or a brother (next task)
        # We check that the last stage was over
        while stack and stack[-1].was_finished():
            stack.pop()
            # treat it as a brother

        stack.append(ProgressStage(taskname, iterations, iteration_desc))
        progress_stack_updated()
