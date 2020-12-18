from zuper_commons.types import check_isinstance
from .exceptions import JobFailed
from .exceptions import HostFailed
from .exceptions import CompmakeBug
from .exceptions import JobInterrupted

__all__ = [
    "result_dict_check",
    "result_dict_raise_if_error",
]


def result_dict_check(res):
    check_isinstance(res, dict)
    # print(res.__repr__().__repr__()) # XXX
    msg = "Invalid result dict"  #% res
    # print('result_dict: %s' % res)
    if "new_jobs" in res:
        assert "new_jobs" in res, msg
        assert "deleted_jobs" in res, msg
        assert "user_object_deps" in res, msg
    elif "fail" in res:
        assert "deleted_jobs" in res, msg
    elif "bug" in res:
        pass
    elif "abort" in res:
        pass
    elif "interrupted" in res:
        assert "deleted_jobs" in res, msg
        pass
    else:
        msg = "Malformed result dict: %s" % res
        raise ValueError(msg)


def result_dict_raise_if_error(res):

    result_dict_check(res)

    if "fail" in res:
        raise JobFailed.from_dict(res)

    if "abort" in res:
        raise HostFailed.from_dict(res)

    if "bug" in res:
        raise CompmakeBug.from_dict(res)

    if "interrupted" in res:
        raise JobInterrupted.from_dict(res)
