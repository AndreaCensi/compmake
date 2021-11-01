import pickle

from . import logger

__all__ = [
    "safe_pickle_dump",
    "safe_pickle_load",
]

from zuper_commons.fs import safe_pickle_dump, safe_pickle_load

_ = safe_pickle_dump, safe_pickle_load
