"""
    These are all wrappers around the raw methods in storage
"""
from typing import Any, Callable, cast, Collection, Iterator, Mapping

from compmake_utils.pickle_frustration import pickle_main_context_load
from zuper_commons.text import wildcard_to_regexp
from zuper_commons.types import check_isinstance
from .exceptions import CompmakeBug, CompmakeDBError, CompmakeException
from .filesystem import StorageFilesystem, StorageKey
from .structures import Cache, Job
from .types import CMJobID

__all__ = [
    "all_jobs",
    "assert_job_exists",
    "db_job_add_dynamic_children",
    "db_job_add_parent",
    "db_job_add_parent_relation",
    "delete_all_job_data",
    "delete_job",
    "delete_job_args",
    "delete_job_cache",
    "delete_job_userobject",
    "get_job",
    "get_job_args",
    "get_job_cache",
    "get_job_userobject",
    "is_job_userobject_available",
    "job2cachekey",
    "job2jobargskey",
    "job2key",
    "job2userobjectkey",
    "job_args_exists",
    "job_args_sizeof",
    "job_cache_exists",
    "job_cache_sizeof",
    "job_exists",
    "job_userobject_exists",
    "job_userobject_sizeof",
    "key2job",
    "set_job",
    "set_job_args",
    "set_job_cache",
    "set_job_userobject",
]
KEY_JOB_PREFIX = "cm-job-"


def job2key(job_id: CMJobID) -> StorageKey:
    return cast(StorageKey, f"{KEY_JOB_PREFIX}{job_id}")


def key2job(key: StorageKey) -> CMJobID:
    return CMJobID(key.replace(KEY_JOB_PREFIX, "", 1))


def all_jobs(db: StorageFilesystem, force_db: bool = False) -> Iterator[CMJobID]:
    """Returns the list of all jobs.
    If force_db is True, read jobs from DB.
    Otherwise, use local cache.
    """
    pattern = job2key(CMJobID("*"))
    regexp = wildcard_to_regexp(pattern)

    for key in db.keys():
        if regexp.match(key):
            yield key2job(key)


def get_job(job_id: CMJobID, db: StorageFilesystem) -> Job:
    key = job2key(job_id)
    computation = db[key]
    assert isinstance(computation, Job)
    return computation


def job_exists(job_id: CMJobID, db: StorageFilesystem) -> bool:
    key = job2key(job_id)
    return key in db


def assert_job_exists(job_id: CMJobID, db: StorageFilesystem):
    """
    :raise CompmakeBug: if the job does not exist
    """
    get_job(job_id, db)


def set_job(job_id: CMJobID, job: Job, db: StorageFilesystem) -> None:
    # TODO: check if they changed
    key = job2key(job_id)
    assert isinstance(job, Job)
    db[key] = job


def delete_job(job_id: CMJobID, db: StorageFilesystem) -> None:
    key = job2key(job_id)
    del db[key]


#
# Cache objects
#
def job2cachekey(job_id: CMJobID) -> StorageKey:
    prefix = "cm-cache-"
    return cast(StorageKey, f"{prefix}{job_id}")


def get_job_cache(job_id: CMJobID, db: StorageFilesystem) -> Cache:
    assert isinstance(job_id, str)
    # assert isinstance(db, StorageFilesystem)
    cache_key = job2cachekey(job_id)
    if cache_key in db:
        try:
            cache = db[cache_key]
            assert isinstance(cache, Cache)
        except Exception as e:
            del db[cache_key]
            # also remove user object?
            msg = f'Could not read Cache object for job "{job_id}": {e}; deleted.'
            raise CompmakeException(msg)
        return cache
    else:
        # make sure this is a valid job_id
        # XXX expensive
        # known = all_jobs()
        # if not job_id in known:
        # raise CompmakeException("invalid job %s, I know %s"
        # % (job_id, known))
        if not job_exists(job_id, db):
            msg = "Requesting cache for job that does not exist."
            raise CompmakeDBError(msg, job_id=job_id)

    cache = Cache(Cache.NOT_STARTED)
    # we only put it later: NOT_STARTEd == not existent
    # get_compmake_db().set(cache_key, cache)
    return cache


def job_cache_exists(job_id: CMJobID, db: StorageFilesystem) -> bool:
    key = job2cachekey(job_id)
    return key in db


def job_cache_sizeof(job_id: CMJobID, db: StorageFilesystem) -> int:
    key = job2cachekey(job_id)
    return db.sizeof(key)


def set_job_cache(job_id: CMJobID, cache: Cache, db: StorageFilesystem) -> None:
    assert isinstance(cache, Cache)
    check_isinstance(cache.captured_stderr, (type(None), str))
    check_isinstance(cache.captured_stdout, (type(None), str))
    check_isinstance(cache.exception, (type(None), str))
    check_isinstance(cache.backtrace, (type(None), str))
    key = job2cachekey(job_id)
    db[key] = cache


def delete_job_cache(job_id: CMJobID, db: StorageFilesystem) -> None:
    key = job2cachekey(job_id)
    del db[key]


#
# User objects
#
def job2userobjectkey(job_id: CMJobID) -> StorageKey:
    prefix = "cm-res-"
    return cast(StorageKey, f"{prefix}{job_id}")


def get_job_userobject(job_id: CMJobID, db: StorageFilesystem) -> object:
    # available = is_job_userobject_available(job_id, db)
    # if not available:
    # available_job = job_exists(job_id, db)
    #         available_cache = job_cache_exists(job_id, db)
    #         msg = 'Job user object %r does not exist.' % job_id
    #         msg += ' Job exists: %s. Cache exists: %s. ' % (available_job,
    #  available_cache)
    #         msg += '\n jobs: %s' % list(all_jobs(db))
    #         msg += '\n path: %s' % db.basepath
    #         raise CompmakeBug(msg)
    # print('loading %r ' % job_id)
    key = job2userobjectkey(job_id)
    res = db[key]
    # print('... done')
    return res


def job_userobject_sizeof(job_id: CMJobID, db: StorageFilesystem) -> int:
    key = job2userobjectkey(job_id)
    return db.sizeof(key)


def is_job_userobject_available(job_id: CMJobID, db: StorageFilesystem) -> bool:
    key = job2userobjectkey(job_id)
    return key in db


job_userobject_exists = is_job_userobject_available


def set_job_userobject(job_id: CMJobID, obj: object, db: StorageFilesystem) -> None:
    key = job2userobjectkey(job_id)
    db[key] = obj


def delete_job_userobject(job_id: CMJobID, db: StorageFilesystem) -> None:
    key = job2userobjectkey(job_id)
    del db[key]


def job2jobargskey(job_id: CMJobID) -> StorageKey:
    prefix = "cm-args-"
    return cast(StorageKey, f"{prefix}{job_id}")


def get_job_args(job_id: CMJobID, db: StorageFilesystem) -> tuple[Callable[..., Any], tuple[Any, ...], Mapping[str, Any]]:
    key = job2jobargskey(job_id)

    # if False:
    #     return db[key]
    # else:
    job = get_job(job_id, db)
    pickle_main_context = job.pickle_main_context
    with pickle_main_context_load(pickle_main_context):
        return db[key]  # type: ignore
        # TODO: check?


def job_args_exists(job_id: CMJobID, db: StorageFilesystem) -> bool:
    key = job2jobargskey(job_id)
    return key in db


def job_args_sizeof(job_id: CMJobID, db: StorageFilesystem) -> int:
    key = job2jobargskey(job_id)
    return db.sizeof(key)


def set_job_args(job_id: CMJobID, obj: object, db: StorageFilesystem) -> None:
    key = job2jobargskey(job_id)

    db[key] = obj


def delete_job_args(job_id: CMJobID, db: StorageFilesystem) -> None:
    key = job2jobargskey(job_id)
    del db[key]


def delete_all_job_data(job_id: CMJobID, db: StorageFilesystem) -> None:
    # print('deleting_all_job_data(%r)' % job_id)
    if job_exists(job_id=job_id, db=db):
        delete_job(job_id=job_id, db=db)
    if job_args_exists(job_id=job_id, db=db):
        delete_job_args(job_id=job_id, db=db)
    if job_userobject_exists(job_id=job_id, db=db):
        delete_job_userobject(job_id=job_id, db=db)
    if job_cache_exists(job_id=job_id, db=db):
        delete_job_cache(job_id=job_id, db=db)


# These are delicate and should be implemented differently
def db_job_add_dynamic_children(
    job_id: CMJobID, children: Collection[CMJobID], returned_by: CMJobID, db: StorageFilesystem
) -> None:
    job = get_job(job_id, db)
    if not returned_by in job.children:
        msg = f"{job_id!r} does not know it has child  {returned_by!r}"
        raise CompmakeBug(msg)

    job.children.update(children)
    job.dynamic_children[returned_by] = set(children)
    set_job(job_id, job, db)
    job2 = get_job(job_id, db)
    assert job2.children == job.children, "Race condition"
    assert job2.dynamic_children == job.dynamic_children, "Race condition"


def db_job_add_parent(db: StorageFilesystem, job_id: CMJobID, parent: CMJobID) -> None:
    j = get_job(job_id, db)
    # print('%s old parents list: %s' % (d, j.parents))
    j.parents.add(parent)
    set_job(job_id, j, db)
    j2 = get_job(job_id, db)
    assert j2.parents == j.parents, "Race condition"  # FIXME


def db_job_add_parent_relation(child: CMJobID, parent: CMJobID, db: StorageFilesystem) -> None:
    child_comp = get_job(child, db=db)
    orig = set(child_comp.parents)
    want = orig | {parent}
    # alright, need to take care of race condition
    while True:
        # Try to write
        child_comp.parents = want
        set_job(child, child_comp, db=db)
        # now read back
        child_comp = get_job(child, db=db)
        if child_comp.parents != want:
            print(f"race condition for parents of {child}")
            print(f"orig: {orig}")
            print(f"want: {want}")
            print(f"now: {child_comp.parents}")
            # add the children of the other racers as well
            want = want | child_comp.parents
        else:
            break
