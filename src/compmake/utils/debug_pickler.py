# -*- coding: utf-8 -*-
import pickle
from io import BytesIO as StringIO
# noinspection PyProtectedMember
from pickle import (
    EMPTY_TUPLE, MARK, POP, POP_MARK, Pickler, SETITEM, SETITEMS, TUPLE,
    _tuplesize2code)

from contracts import describe_type
from past.builtins import xrange

from .. import logger

__all__ = [
    'find_pickling_error',
]
import traceback


def find_pickling_error(obj, protocol=pickle.HIGHEST_PROTOCOL):
    sio = StringIO()
    try:
        pickle.dumps(obj)
    except Exception:
        msg_old = '\n --- Old exception----\n%s' % traceback.format_exc()

    else:
        msg_old = ''
        msg = ('Strange! I could not reproduce the pickling error '
               'for the object of class %s' % describe_type(obj))
        logger.info(msg)

    pickler = MyPickler(sio, protocol)
    try:
        pickler.dump(obj)
    except Exception as e1:
        msg = pickler.get_stack_description()

        msg += '\n --- Current exception----\n%s' % traceback.format_exc()
        msg += msg_old
        return msg
    else:
        msg = 'I could not find the exact pickling error.'
        raise Exception(msg)


class MyPickler(Pickler):
    def __init__(self, *args, **kargs):
        Pickler.__init__(self, *args, **kargs)
        self.stack = []

    def save(self, obj):
        desc = 'object of type %s' % (describe_type(obj))
        # , describe_value(obj, 100))
        # self.stack.append(describe_value(obj, 120))
        self.stack.append(desc)
        Pickler.save(self, obj)
        self.stack.pop()

    def get_stack_description(self):
        s = 'Pickling error occurred at:\n'
        for i, context in enumerate(self.stack):
            s += ' ' * i + '- %s\n' % context
        return s

    def save_pair(self, k, v):
        self.stack.append('key %r = object of type %s' % (k, describe_type(v)))
        self.save(k)
        self.save(v)
        self.stack.pop()

    def _batch_setitems(self, items):

        # Helper to batch up SETITEMS sequences; proto >= 1 only
        # save = self.save
        write = self.write

        if not self.bin:
            for k, v in items:
                self.stack.append('entry %s' % str(k))
                self.save_pair(k, v)
                self.stack.pop()
                write(SETITEM)
            return

        r = xrange(self._BATCHSIZE)
        while items is not None:
            tmp = []
            for _ in r:
                try:
                    tmp.append(items.next())
                except StopIteration:
                    items = None
                    break
            n = len(tmp)
            if n > 1:
                write(MARK)
                for k, v in tmp:
                    self.stack.append('entry %s' % str(k))
                    self.save_pair(k, v)
                    self.stack.pop()
                write(SETITEMS)
            elif n:
                k, v = tmp[0]
                self.stack.append('entry %s' % str(k))
                self.save_pair(k, v)
                self.stack.pop()
                write(SETITEM)
                # else tmp is empty, and we're done

    def save_tuple(self, obj):
        write = self.write
        proto = self.proto

        n = len(obj)
        if n == 0:
            if proto:
                write(EMPTY_TUPLE)
            else:
                write(MARK + TUPLE)
            return

        save = self.save
        memo = self.memo
        if n <= 3 and proto >= 2:
            for i, element in enumerate(obj):
                self.stack.append('tuple element %s' % i)
                save(element)
                self.stack.pop()
            # Subtle.  Same as in the big comment below.
            if id(obj) in memo:
                get = self.get(memo[id(obj)][0])
                write(POP * n + get)
            else:
                write(_tuplesize2code[n])
                self.memoize(obj)
            return

        # proto 0 or proto 1 and tuple isn't empty, or proto > 1 and tuple
        # has more than 3 elements.
        write(MARK)
        for i, element in enumerate(obj):
            self.stack.append('tuple element %s' % i)
            save(element)
            self.stack.pop()

        if id(obj) in memo:
            # Subtle.  d was not in memo when we entered save_tuple(), so
            # the process of saving the tuple's elements must have saved
            # the tuple itself:  the tuple is recursive.  The proper action
            # now is to throw away everything we put on the stack, and
            # simply GET the tuple (it's already constructed).  This check
            # could have been done in the "for element" loop instead, but
            # recursive tuples are a rare thing.
            get = self.get(memo[id(obj)][0])
            if proto:
                write(POP_MARK + get)
            else:  # proto 0 -- POP_MARK not available
                write(POP * (n + 1) + get)
            return

        # No recursion.
        self.write(TUPLE)
        self.memoize(obj)
