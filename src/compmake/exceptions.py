from typing import List

from zuper_commons.text import indent
from zuper_commons.types import raise_wrapped, ZException


class ShellExitRequested(ZException):
    pass


class CompmakeException(ZException):
    pass


class CompmakeDBError(CompmakeException):
    """ Raised for inconsistencies in the DB. """


class CompmakeBug(CompmakeException):
    def get_result_dict(self):
        res = dict(bug=str(self))
        return res

    @staticmethod
    def from_dict(res):
        from compmake.jobs.result_dict import result_dict_check

        result_dict_check(res)
        assert "bug" in res
        e = CompmakeBug(res["bug"])
        return e


class CommandFailed(ZException):
    pass


class MakeFailed(CommandFailed):
    def __init__(self, failed: List[str], blocked: List[str] = None):
        failed = failed or []
        blocked = blocked or []
        self.failed = set(failed)
        self.blocked = set(blocked)
        msg = f"Make failed ({len(self.failed)} failed, {len(self.blocked)} blocked)"
        CommandFailed.__init__(self, msg, failed=failed, blocked=blocked)


class MakeHostFailed(CommandFailed):
    # Thrown when all workers have aborted
    pass


class KeyNotFound(CompmakeException):
    pass


class UserError(CompmakeException):
    pass


class SerializationError(UserError):
    """ Something cannot be serialized (function or function result)."""

    pass


class CompmakeSyntaxError(UserError):
    pass


class JobFailed(CompmakeException):
    """ This signals that some job has failed """

    def __init__(self, job_id: str, reason: str, bt: str, deleted_jobs: List[str] = None):
        deleted_jobs = deleted_jobs or []
        self.job_id = job_id
        self.reason = reason
        self.bt = bt
        self.deleted_jobs = set(deleted_jobs)

        CompmakeException.__init__(self, job_id=job_id, reason=reason, bt=bt, deleted_jobs=deleted_jobs)

    def get_result_dict(self):
        res = dict(
            fail=f"Job {self.job_id!r} failed.",
            job_id=self.job_id,
            reason=self.reason,
            deleted_jobs=self.deleted_jobs,
            bt=self.bt,
        )
        return res

    @staticmethod
    def from_dict(res):
        from compmake.jobs.result_dict import result_dict_check

        result_dict_check(res)
        assert "fail" in res
        e = JobFailed(
            job_id=res["job_id"], bt=res["bt"], reason=res["reason"], deleted_jobs=res["deleted_jobs"]
        )
        return e


class JobInterrupted(CompmakeException):
    """ User requested to interrupt job"""

    def __init__(self, job_id, deleted_jobs: List[str] = None):
        deleted_jobs = deleted_jobs or []
        self.job_id = job_id
        self.deleted_jobs = set(deleted_jobs)

        self.msg = f"Job {self.job_id!r} received KeyboardInterrupt."
        CompmakeException.__init__(self, self.msg, job_id=job_id, deleted_jobs=deleted_jobs)

    def __str__(self):
        return self.msg

    @staticmethod
    def from_dict(res):
        from compmake.jobs.result_dict import result_dict_check

        result_dict_check(res)
        assert "interrupted" in res
        e = JobInterrupted(job_id=res["job_id"], deleted_jobs=res["deleted_jobs"])
        return e

    def get_result_dict(self):
        res = dict(
            interrupt=f"Job {self.job_id!r} interrupted.",
            job_id=self.job_id,
            deleted_jobs=sorted(self.deleted_jobs),
        )
        return res


class HostFailed(CompmakeException):
    """ The job has been interrupted and must
        be redone (it has not failed, though) """

    def __init__(self, host, job_id, reason, bt):
        self.host = host
        self.job_id = job_id
        self.reason = reason
        self.bt = bt
        self.msg = "Host %r failed for %r: %s\n%s" % (
            self.host,
            self.job_id,
            self.reason,
            indent(self.bt, "|"),
        )
        CompmakeException.__init__(self, self.msg, host=host, reason=reason, bt=bt)

    def __str__(self):
        return self.msg

    def get_result_dict(self):
        res = dict(
            abort=f"Host failed for {self.job_id!r}.",
            host=self.host,
            job_id=self.job_id,
            reason=self.reason,
            bt=self.bt,
        )
        return res

    @staticmethod
    def from_dict(res):
        from compmake.jobs.result_dict import result_dict_check

        result_dict_check(res)
        try:
            _ = res["abort"]
            e = HostFailed(host=res["host"], job_id=res["job_id"], bt=res["bt"], reason=res["reason"])
        except KeyError as e:
            raise_wrapped(CompmakeBug, e, "Incomplete dict", res=res, keys=list(res.keys()))

        return e
