import functools
from typing import TYPE_CHECKING, TypeVar

__all__ = [
    "memoized_reset",
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
X = TypeVar("X")
if TYPE_CHECKING:

    def memoized_reset(x: X) -> X:
        return x

else:

    class memoized_reset:
        """Decorator that caches a function's return value each time it is called.
        If called later with the same arguments, the cached value is returned, and
        not re-evaluated.
        """

        def __init__(self, func):
            self.func = func

        def _getcache_ob(self, the_ob):
            if not hasattr(the_ob, "memoized_reset_cache"):
                setattr(the_ob, "memoized_reset_cache", {})
            cache_ob = getattr(the_ob, "memoized_reset_cache")
            return cache_ob

        def _deletefunccache(self, the_ob) -> None:
            cache_ob = self._getcache_ob(the_ob)
            funcname = self.func.__name__
            cache_ob.pop(funcname, None)

        def _getcache(self, the_ob) -> dict:
            cache_ob = self._getcache_ob(the_ob)
            funcname = self.func.__name__
            if funcname not in cache_ob:
                cache_ob[funcname] = {}
            return cache_ob[funcname]

        def __call__(self, the_ob, *args):

            cache = self._getcache(the_ob)

            is_key_error = is_type_error = False
            try:
                res = cache[args]
                # print(f"using cache for {self.func}({args} = {res}")
                return res
            except KeyError:
                is_key_error = True
            except TypeError:
                is_type_error = True

            if is_key_error:
                value = self.func(the_ob, *args)
                cache[args] = value
                return value
            if is_type_error:
                # uncachable -- for instance, passing a list as an argument.
                # Better to not cache than to blow up entirely.
                return self.func(*args)

        def __repr__(self):
            """Return the function's docstring."""
            return self.func.__doc__

        def __get__(self, obj, objtype):
            """Support instance methods."""
            fn = functools.partial(self.__call__, obj)
            fn.reset = functools.partial(self._deletefunccache, obj)
            return fn
