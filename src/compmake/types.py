from typing import List, NewType, Set, TypedDict, Union

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
    user_object_deps: Set[CMJobID]
    new_jobs: Set[CMJobID]
    deleted_jobs: Set[CMJobID]


class OKResult(TypedDict):
    job_id: CMJobID
    new_jobs: List[CMJobID]
    deleted_jobs: List[CMJobID]
    user_object_deps: List[CMJobID]


class FailResult(TypedDict):
    job_id: CMJobID
    fail: str
    # new_jobs: List[CMJobID]
    deleted_jobs: List[CMJobID]
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
    deleted_jobs: List[CMJobID]


ResultDict = Union[OKResult, FailResult, BugResult, InterruptedResult, AbortResult]
