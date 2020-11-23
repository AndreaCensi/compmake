from contextlib import contextmanager
import sys

import time


__all__ = [
    "TimeTrack",
]


class TimeTrack:
    def __init__(self, what=None):
        self.t0 = time.time()
        self.c0 = time.process_time()
        self.what = what

    def show(self, stream=sys.stdout, min_td=0.001):
        self.t1 = time.time()
        self.c1 = time.process_time()
        self.cd = self.c1 - self.c0
        self.td = self.t1 - self.t0

        if self.td < min_td:
            return

        msg = "wall %6.2fms clock %6.2fms" % (self.td * 1000, self.cd * 1000)
        if self.what:
            what = str(self.what)
            MAX = 120
            if len(what) > MAX:
                what = what[: (MAX - 3)] + "..."
            # msg = '%s - %s' % (msg, what)
            msg = "%s - %s" % (msg, what)
        # stream.write(msg)
        #         stream.write('\n')
        #         stream.flush()
        from compmake import logger

        logger.warning(msg)

    @staticmethod
    @contextmanager
    def measure(what=None, min_td=0.001):
        t = TimeTrack(what)
        yield
        t.show(min_td=min_td)

    @staticmethod
    def decorator(f):
        def wrapper(self, *args, **kwargs):
            sargs = ", ".join(["{0}".format(x) for x in args])
            if args and kwargs:
                sargs += ", "
            sargs += ", ".join([f"{k}={v!r}" for (k, v) in kwargs.items()])
            what = f"{f.__name__:>15}({sargs})"
            with TimeTrack.measure(what, min_td=0.1):
                return f(self, *args, **kwargs)

        return wrapper
