import pickle

from compmake import logger

__all__ = [
    "safe_pickle_dump",
    "safe_pickle_load",
]
from zuper_commons.fs import safe_write, find_pickling_error, safe_read
from zuper_commons.types import describe_type


def safe_pickle_dump(value, filename, protocol=pickle.HIGHEST_PROTOCOL, **safe_write_options):
    with safe_write(filename, **safe_write_options) as f:
        try:
            pickle.dump(value, f, protocol)
        except KeyboardInterrupt:
            raise
        except Exception:
            msg = "Cannot pickle object of class %s" % describe_type(value)
            logger.error(msg)
            msg = find_pickling_error(value, protocol)
            logger.error(msg)
            raise


def safe_pickle_load(filename):
    # TODO: add debug check
    with safe_read(filename) as f:
        return pickle.load(f)
        # TODO: add pickling debug
