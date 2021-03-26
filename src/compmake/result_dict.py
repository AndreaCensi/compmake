from zuper_commons.types import check_isinstance, ZAssertionError
from .exceptions import CompmakeBug, HostFailed, JobFailed, JobInterrupted
from .types import OKResult, ResultDict

__all__ = [
    "result_dict_check",
    "result_dict_raise_if_error",
    "check_ok_result",
]


def check_ok_result(res: ResultDict) -> OKResult:
    try:
        # print('result_dict: %s' % res)

        assert "new_jobs" in res
        assert "deleted_jobs" in res
        assert "user_object_deps" in res

        assert not "fail" in res
        assert not "bug" in res
        assert not "abort" in res
        assert not "interrupted" in res

    except AssertionError:
        msg = "Invalid type for OKResult"
        raise ZAssertionError(msg, res=res)

    return res


def result_dict_check(res: ResultDict):
    check_isinstance(res, dict)
    # print(res.__repr__().__repr__()) # XXX
    msg = "Invalid result dict"  # % res
    try:
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
    except AssertionError:
        msg = "Invalid type of result dict"
        raise ZAssertionError(msg, res=res)


def result_dict_raise_if_error(res: ResultDict) -> OKResult:
    result_dict_check(res)

    if "fail" in res:
        raise JobFailed.from_dict(res)

    if "abort" in res:
        raise HostFailed.from_dict(res)

    if "bug" in res:
        raise CompmakeBug.from_dict(res)

    if "interrupted" in res:
        raise JobInterrupted.from_dict(res)

    return res
