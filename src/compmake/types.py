from typing import NewType, TypedDict, Union

__all__ = [
    "AbortResult",
    "BugResult",
    "CMJobID",
    "FailResult",
    "InterruptedResult",
    "MakeResult",
    "OKResult",
    "ResultDict",
]
CMJobID = NewType("CMJobID", str)


class MakeResult(TypedDict):  # XXX
    user_object: object
    user_object_deps: set[CMJobID]
    new_jobs: set[CMJobID]
    deleted_jobs: set[CMJobID]

    time_total: float
    time_comp: float
    time_other: float


class OKResult(TypedDict):
    job_id: CMJobID
    new_jobs: list[CMJobID]
    deleted_jobs: list[CMJobID]
    user_object_deps: list[CMJobID]


class FailResult(TypedDict):
    job_id: CMJobID
    fail: str
    # new_jobs: List[CMJobID]
    deleted_jobs: list[CMJobID]
    bt: str
    reason: str


class BugResult(TypedDict):
    job_id: CMJobID
    bug: object


class AbortResult(TypedDict):
    job_id: CMJobID
    abort: str

    host: str
    bt: str
    reason: str


class InterruptedResult(TypedDict):
    job_id: CMJobID
    interrupt: str
    deleted_jobs: list[CMJobID]


ResultDict = Union[OKResult, FailResult, BugResult, InterruptedResult, AbortResult]
