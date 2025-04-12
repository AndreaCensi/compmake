# -*- coding: utf-8 -*-
"""
Compatibility layer for different Python versions.
"""
import sys
import time

# time.clock() was removed in Python 3.8, use time.perf_counter() instead
# See: https://docs.python.org/3/library/time.html#time.clock
if hasattr(time, 'perf_counter'):
    # Python 3.3+
    def get_cpu_time():
        return time.perf_counter()
elif hasattr(time, 'clock'):
    # Python 2.x and early Python 3.x
    def get_cpu_time():
        return time.clock()
else:
    # Fallback to time.time() if neither is available
    def get_cpu_time():
        return time.time()

__all__ = ['get_cpu_time']