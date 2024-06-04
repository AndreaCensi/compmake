from typing import cast

from zuper_commons.types import ZAssertionError, check_isinstance
from .exceptions import CompmakeBug, HostFailed, JobFailed, JobInterrupted
from .types import OKResult, ResultDict

__all__ = [
    "check_ok_result",
    "result_dict_check",
    "result_dict_raise_if_error",
]


def check_ok_result(res: ResultDict) -> OKResult:
    ok = True
    ok &= "new_jobs" in res
    ok &= "deleted_jobs" in res
    ok &= "user_object_deps" in res

    ok &= not "fail" in res
    ok &= not "bug" in res
    ok &= not "abort" in res
    ok &= not "interrupted" in res

    if not ok:
        msg = "Invalid type for OKResult"
        raise ZAssertionError(msg, res=res)

    return cast(OKResult, res)


def result_dict_check(res: ResultDict) -> None:
    check_isinstance(res, dict)
    # print(res.__repr__().__repr__()) # XXX
    # msg = "Invalid result dict"  # % res
    # print('result_dict: %s' % res)
    ok = True
    if "new_jobs" in res:
        ok &= "new_jobs" in res
        ok &= "deleted_jobs" in res
        ok &= "user_object_deps" in res
    elif "fail" in res:
        ok &= "deleted_jobs" in res
    elif "bug" in res:
        pass
    elif "abort" in res:
        pass
    elif "interrupted" in res:
        ok &= "deleted_jobs" in res
    else:
        msg = "Malformed result dict: %s" % res
        raise ValueError(msg)
    if not ok:
        msg = "Invalid type of result dict"
        raise ZAssertionError(msg, res=res)


from .types import FailResult, AbortResult, BugResult, InterruptedResult


def result_dict_raise_if_error(res: ResultDict) -> OKResult:
    result_dict_check(res)

    if "fail" in res:
        raise JobFailed.from_dict(cast(FailResult, res))

    if "abort" in res:
        raise HostFailed.from_dict(cast(AbortResult, res))

    if "bug" in res:
        raise CompmakeBug.from_dict(cast(BugResult, res))

    if "interrupted" in res:
        raise JobInterrupted.from_dict(cast(InterruptedResult, res))
    return cast(OKResult, res)
