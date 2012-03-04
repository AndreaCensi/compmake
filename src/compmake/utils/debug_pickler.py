from . import describe_type
from StringIO import StringIO
from pickle import Pickler, SETITEM, MARK, SETITEMS


def find_pickling_error(obj):
    sio = StringIO()
    pickler = MyPickler(sio)
    try:
        pickler.dump(obj)
    except:
        return pickler.get_stack_description()
    else:
        raise Exception('We could pickle this object.')


class MyPickler (Pickler):
    def __init__(self, *args, **kargs):
        Pickler.__init__(self, *args, **kargs)
        self.stack = []

    def save(self, obj):
        desc = '%30s' % (describe_type(obj))
        #, describe_value(obj, 100))
        #  self.stack.append(describe_value(obj, 120))
        self.stack.append(desc)
        Pickler.save(self, obj)
        self.stack.pop()

    def get_stack_description(self):
        s = 'Pickling error occurred at:'
        for context in self.stack:
            s += '- %s\n' % context
        return s

    def save_pair(self, k, v):
        self.save(k)
        self.stack.append('key %r' % k)
        self.save(v)
        self.stack.pop()

    def _batch_setitems(self, items):
        # Helper to batch up SETITEMS sequences; proto >= 1 only
        #save = self.save
        write = self.write

        if not self.bin:
            for k, v in items:
                self.save_pair(k, v)
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
                    self.save_pair(k, v)
                write(SETITEMS)
            elif n:
                k, v = tmp[0]
                self.save_pair(k, v)
                write(SETITEM)
            # else tmp is empty, and we're done
