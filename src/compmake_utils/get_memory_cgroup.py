import os
from dataclasses import dataclass

import psutil

from zuper_commons.types import ZException

__all__ = [
    "CannotGetMemory",
    "MemoryUsageStats",
    "get_memory_usage",
]


class CannotGetMemory(ZException):
    pass


@dataclass
class MemoryUsageStats:
    method: str
    limit: int
    usage: int
    usage_percent: float


def get_memory_cgroup() -> MemoryUsageStats:
    a = "/sys/fs/cgroup/memory/memory.limit_in_bytes"
    b = "/sys/fs/cgroup/memory/memory.usage_in_bytes"
    if not os.path.exists(a) or not os.path.exists(b):
        raise CannotGetMemory("cgroups do not exist")

    with open(a) as f:
        s = f.read()
        limit_in_bytes = int(s)
    with open(b) as f:
        s = f.read()
        usage_in_bytes = int(s)

    usage_percent = usage_in_bytes * 100.0 / limit_in_bytes
    return MemoryUsageStats("cgroup", limit_in_bytes, usage_in_bytes, usage_percent)


def get_memory_psutil() -> MemoryUsageStats:
    mem = psutil.virtual_memory()
    total = mem.total
    used = mem.used
    percent = mem.percent
    return MemoryUsageStats("psutil", total, used, percent)


def get_memory_usage() -> MemoryUsageStats:
    try:
        return get_memory_cgroup()
    except CannotGetMemory:
        return get_memory_psutil()
