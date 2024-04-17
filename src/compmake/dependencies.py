from copy import deepcopy
from typing import Any, TypeVar

from zuper_commons.types import ZException, ZValueError
from .exceptions import CompmakeBug
from .filesystem import StorageFilesystem
from .storage import get_job_userobject, job_userobject_exists
from .structures import Promise
from .types import CMJobID

__all__ = [
    "collect_dependencies",
    "get_job_userobject_resolved",
    "substitute_dependencies",
]


def get_job_userobject_resolved(job_id: CMJobID, db: StorageFilesystem) -> object:
    """This gets the job's result, and recursively substitute all
    dependencies."""
    ob = get_job_userobject(job_id, db)
    all_deps = collect_dependencies(ob)
    for dep in all_deps:
        if not job_userobject_exists(dep, db):
            msg = f"Cannot resolve {job_id!r}: dependency {dep!r} was not done."
            raise CompmakeBug(msg)
    return substitute_dependencies(ob, db)


X = TypeVar("X")


def substitute_dependencies(a: X, db: StorageFilesystem) -> X:
    # XXX: this is a workaround
    if leave_it_alone(a):
        return deepcopy(a)

    if isinstance(a, dict):
        ca = type(a)
        rest = [(k, substitute_dependencies(v, db=db)) for k, v in a.items()]
        try:
            # noinspection PyArgumentList
            res = ca(rest)
            # print('%s->%s' % (a, str(res)))
            return res
        except (BaseException, TypeError) as e:
            msg = "Could not instance something looking like a dict."
            raise ZException(msg, ca=ca) from e

    elif isinstance(a, list):
        # XXX: This fails for subclasses of list
        # noinspection PyArgumentList
        return type(a)([substitute_dependencies(x, db=db) for x in a])
    elif isinstance(a, tuple):
        # First, check that there are dependencies
        deps_in_tuple = collect_dependencies(a)
        if not deps_in_tuple:
            # if not, just return the tuple
            return a
        # XXX: This fails for subclasses of tuples
        assert not isnamedtupleinstance(a), a

        ta = type(a)
        contents = [substitute_dependencies(x, db=db) for x in a]
        try:
            # noinspection PyArgumentList
            return ta(contents)
        except TypeError as e:
            msg = "Cannot reconstruct complex tuple."
            raise ZValueError(msg, ta=ta, contents=contents) from e
    elif isinstance(a, Promise):
        s = get_job_userobject(a.job_id, db=db)
        return substitute_dependencies(s, db=db)
    else:
        return a


def collect_dependencies(ob: Any) -> set[CMJobID]:
    """Returns a set of dependencies (i.e., Promise objects that
    are mentioned somewhere in the structure"""

    if isinstance(ob, Promise):
        return {ob.job_id}
    else:
        if leave_it_alone(ob):
            return set()

        depends: set[CMJobID] = set()
        child: object
        if isinstance(ob, (list, tuple)):
            for child in ob:
                depends.update(collect_dependencies(child))
        if isinstance(ob, dict):
            for child in ob.values():
                depends.update(collect_dependencies(child))
        return depends


def leave_it_alone(x: object) -> bool:
    """Returns True for those objects that have trouble with factory methods
    like namedtuples."""
    if isnamedtupleinstance(x):
        return True

    # XXX: this is a workaround
    if type(x).__name__ in ["ObjectSpec"]:
        return True

    return False


def isnamedtupleinstance(x: Any) -> bool:
    t = type(x)
    b = t.__bases__
    if len(b) != 1 or b[0] != tuple:
        return False
    f = getattr(t, "_fields", None)
    if not isinstance(f, tuple):
        return False

    return all(type(n) == str for n in f)
