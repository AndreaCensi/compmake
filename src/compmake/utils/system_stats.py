# -*- coding: utf-8 -*-
import time

__all__ = [
    'AvgSystemStats',
]

try:
    import psutil  # @UnusedImport
except ImportError:
    from compmake import logger

    logger.warning('Package "psutil" not found; load balancing '
                   'and system stats (CPU, MEM) not available.')


class AvgSystemStats(object):
    """ Collects average statistics about the system using psutil. """

    def __init__(self, interval, history_len):
        """

        :param interval: Collect statistics according to this interval.
        :param history_len: Use this many to compute avg/max statistics.
        """

        self.interval = interval
        self.history_len = history_len
        try:
            import psutil  # @UnresolvedImport @Reimport
        except:
            self._available = False
        else:
            self._available = True

            self.cpu = Collect('cpu', lambda: psutil.cpu_percent(interval=0),
                               interval, history_len)

            try:
                # new in 0.8
                psutil.virtual_memory().percent
                get_mem = lambda: psutil.virtual_memory().percent
            except:
                get_mem = lambda: psutil.phymem_usage().percent

            self.mem = Collect('mem', get_mem, interval, history_len)
            try:
                # new in 0.8
                psutil.swap_memory().percent
                get_mem = lambda: psutil.swap_memory().percent
            except:
                get_mem = lambda: psutil.virtmem_usage().percent

            self.swap_mem = Collect('swap', get_mem, interval, history_len)

    def avg_cpu_percent(self):
        self._check_available()
        return self.cpu.get_avg()

    def max_cpu_percent(self):
        self._check_available()
        return self.cpu.get_max()

    def avg_phymem_usage_percent(self):
        self._check_available()
        return self.mem.get_avg()

    def cur_phymem_usage_percent(self):
        self._check_available()
        return self.mem.get_cur()

    def cur_virtmem_usage_percent(self):
        self._check_available()
        return self.swap_mem.get_cur()

    def available(self):
        """ returns false if psutil is not installed """
        return self._available

    def _check_available(self):
        if not self._available:
            msg = 'Sorry, psutil not available.'
            raise ValueError(msg)


class Collect(object):
    def __init__(self, name, function, interval, history_len):
        self.name = name
        self.function = function
        self.interval = interval
        self.history_len = history_len
        self.last_time = None
        self.values = []

    def get_cur(self):
        """ Returns the last value. """
        self.update_if_necessary()
        return self.values[-1]

    def get_min(self):
        self.update_if_necessary()
        return min(self.values)

    def get_max(self):
        self.update_if_necessary()
        return max(self.values)

    def get_avg(self):
        self.update_if_necessary()
        return sum(self.values) * 1.0 / len(self.values)

    def update_if_necessary(self):
        if self.values and self.time_from_last() < self.interval:
            return

        self.values.append(self.function())
        self.last_time = time.time()

        if len(self.values) > self.history_len:
            self.values.pop(0)
            # print('%s: %s' % (self.name, self.values))

    def time_from_last(self):
        if self.last_time is None:
            return self.interval * self.history_len * 2
        else:
            return time.time() - self.last_time
