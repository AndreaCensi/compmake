# -*- coding: utf-8 -*-
import functools


__all__ = [
    'memoized_reset',
]


# def memoize_simple(obj):
# # TODO: make sure it's not iterator
#     cache = obj.cache = {}
# 
#     def memoizer(f, *args, **kwargs):
#         key = (args, frozendict2(kwargs))
#         if key not in cache:
#             cache[key] = f(*args, **kwargs)
#             # print('memoize: %s %d storage' % (obj, len(cache)))
# 
#         return cache[key]
#     
#     return decorator(memoizer, obj)


class memoized_reset(object):
    """Decorator that caches a function's return value each time it is called.
    If called later with the same arguments, the cached value is returned, and
    not re-evaluated.
    """

    def __init__(self, func):
        self.func = func
        self.cache = {}

    def __call__(self, *args):
        try:
            return self.cache[args]
        except KeyError:
            value = self.func(*args)
            self.cache[args] = value
            return value
        except TypeError:
            # uncachable -- for instance, passing a list as an argument.
            # Better to not cache than to blow up entirely.
            return self.func(*args)

    def __repr__(self):
        """Return the function's docstring."""
        return self.func.__doc__

    def __get__(self, obj, objtype):  # @UnusedVariable
        """Support instance methods."""
        fn = functools.partial(self.__call__, obj)
        fn.reset = self._reset
        return fn

    def _reset(self):
        self.cache = {}
