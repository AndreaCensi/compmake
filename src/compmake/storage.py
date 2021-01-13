"""
    These are all wrappers around the raw methods in storage
"""
from typing import cast, Iterator, List

from zuper_commons.types import check_isinstance
from .context import Storage
from .exceptions import CompmakeBug, CompmakeDBError, CompmakeException
from .structures import Cache, Job
from .types import CMJobID, DBKey
from .utils.pickle_frustration import pickle_main_context_load

__all__ = [
    "job2key",
    "key2job",
    "all_jobs",
    "get_job_args",
    "job_args_exists",
    "assert_job_exists",
    "set_job",
    "delete_job",
    "job2cachekey",
    "job_userobject_sizeof",
    "get_job_cache",
    "job_cache_exists",
    "job2jobargskey",
    "is_job_userobject_available",
    "db_job_add_dynamic_children",
    "db_job_add_parent",
    "db_job_add_parent_relation",
    "job_exists",
    "job_cache_sizeof",
    "job_userobject_exists",
    "set_job_args",
    "set_job_cache",
    "set_job_userobject",
    "delete_job_cache",
    "delete_job_userobject",
    "delete_job_args",
    "delete_all_job_data",
    "job2userobjectkey",
    "get_job_userobject",
    "job_args_sizeof",
    "get_job2",
]
KEY_JOB_PREFIX = "cm-job-"


def job2key(job_id: CMJobID) -> DBKey:
    return DBKey(f"{KEY_JOB_PREFIX}{job_id}")


def key2job(key: DBKey) -> CMJobID:
    return CMJobID(key.replace(KEY_JOB_PREFIX, "", 1))


async def all_jobs(db: Storage, force_db: bool = False) -> List[CMJobID]:
    """Returns the list of all jobs.
    If force_db is True, read jobs from DB.
    Otherwise, use local cache.
    """
    res = []
    pattern = job2key(CMJobID("*"))
    async for key in db.list(pattern):
        # regexp = wildcard_to_regexp(pattern)
        #
        # for key in db.keys():
        #     if regexp.match(key):
        res.append(key2job(key))
    return res


async def all_jobs0(db: Storage, force_db: bool = False) -> Iterator[CMJobID]:
    """Returns the list of all jobs.
    If force_db is True, read jobs from DB.
    Otherwise, use local cache.
    """
    pattern = job2key(CMJobID("*"))
    async for key in db.list(pattern):
        # regexp = wildcard_to_regexp(pattern)
        #
        # for key in db.keys():
        #     if regexp.match(key):
        yield key2job(key)


#
# def get_job(job_id: CMJobID, db: Storage) -> Job:
#     key = job2key(job_id)
#     computation = db[key]
#     assert isinstance(computation, Job)
#     return computation


async def get_job2(job_id: CMJobID, db: Storage) -> Job:
    key = job2key(job_id)
    computation = await db.get(key)
    assert isinstance(computation, Job)
    return computation


async def job_exists(job_id: CMJobID, db: Storage) -> bool:
    key = job2key(job_id)
    return await db.contains(key)


async def assert_job_exists(job_id: CMJobID, db: Storage):
    """
    :raise CompmakeBug: if the job does not exist
    """
    await get_job2(job_id, db)


async def set_job(job_id: CMJobID, job: Job, db: Storage) -> None:
    # TODO: check if they changed
    key = job2key(job_id)
    assert isinstance(job, Job)
    await db.set(key, job)


async def delete_job(job_id: CMJobID, db: Storage) -> None:
    key = job2key(job_id)
    await db.remove(key)


#
# Cache objects
#
def job2cachekey(job_id: CMJobID) -> DBKey:
    prefix = "cm-cache-"
    return cast(DBKey, f"{prefix}{job_id}")


async def get_job_cache(job_id: CMJobID, db: Storage):
    assert isinstance(job_id, str)
    # assert isinstance(db, StorageFilesystem)
    cache_key = job2cachekey(job_id)
    if cache_key in db:
        try:
            cache = await db.get(cache_key)
            assert isinstance(cache, Cache)
        except Exception as e:
            await db.remove(cache_key)
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
        if not (await job_exists(job_id, db)):
            msg = "Requesting cache for job that does not exist."
            raise CompmakeDBError(msg, job_id=job_id)

        cache = Cache(Cache.NOT_STARTED)
        # we only put it later: NOT_STARTEd == not existent
        # get_compmake_db().set(cache_key, cache)
        return cache


async def job_cache_exists(job_id: CMJobID, db: Storage) -> bool:
    key = job2cachekey(job_id)
    return await db.contains(key)


async def job_cache_sizeof(job_id: CMJobID, db: Storage) -> int:
    key = job2cachekey(job_id)
    return await db.sizeof(key)


async def set_job_cache(job_id: CMJobID, cache: Cache, db: Storage):
    assert isinstance(cache, Cache)
    check_isinstance(cache.captured_stderr, (type(None), str))
    check_isinstance(cache.captured_stdout, (type(None), str))
    check_isinstance(cache.exception, (type(None), str))
    check_isinstance(cache.backtrace, (type(None), str))
    key = job2cachekey(job_id)
    await db.set(key, cache)


async def delete_job_cache(job_id: CMJobID, db: Storage):
    key = job2cachekey(job_id)
    await db.remove(key)


#
# User objects
#
def job2userobjectkey(job_id: CMJobID) -> DBKey:
    prefix = "cm-res-"
    return cast(DBKey, f"{prefix}{job_id}")


async def get_job_userobject(job_id: CMJobID, db: Storage) -> object:
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
    return await db.get(key)


async def job_userobject_sizeof(job_id: CMJobID, db: Storage) -> int:
    key = job2userobjectkey(job_id)
    return await db.sizeof(key)


async def is_job_userobject_available(job_id: CMJobID, db: Storage) -> bool:
    key = job2userobjectkey(job_id)
    return await db.contains(key)


job_userobject_exists = is_job_userobject_available


async def set_job_userobject(job_id: CMJobID, obj, db: Storage):
    key = job2userobjectkey(job_id)
    await db.set(key, obj)


async def delete_job_userobject(job_id: CMJobID, db: Storage):
    key = job2userobjectkey(job_id)
    await db.remove(key)


def job2jobargskey(job_id: CMJobID) -> DBKey:
    prefix = "cm-args-"
    return cast(DBKey, f"{prefix}{job_id}")


async def get_job_args(job_id: CMJobID, db: Storage):
    key = job2jobargskey(job_id)

    # if False:
    #     return db[key]
    # else:
    job = await get_job2(job_id, db)
    pickle_main_context = job.pickle_main_context
    with pickle_main_context_load(pickle_main_context):
        return await db.get(key)


async def job_args_exists(job_id: CMJobID, db: Storage) -> bool:
    key = job2jobargskey(job_id)
    return await db.contains(key)


async def job_args_sizeof(job_id: CMJobID, db: Storage) -> int:
    key = job2jobargskey(job_id)
    return await db.sizeof(key)


async def set_job_args(job_id: CMJobID, obj, db: Storage):
    key = job2jobargskey(job_id)
    await db.set(key, obj)


async def delete_job_args(job_id: CMJobID, db: Storage):
    key = job2jobargskey(job_id)
    await db.remove(key)


async def delete_all_job_data(job_id: CMJobID, db: Storage):
    # print('deleting_all_job_data(%r)' % job_id)
    args = dict(job_id=job_id, db=db)
    if await job_exists(**args):
        await delete_job(**args)
    if await job_args_exists(**args):
        await delete_job_args(**args)
    if await job_userobject_exists(**args):
        await delete_job_userobject(**args)
    if await job_cache_exists(**args):
        await delete_job_cache(**args)


# These are delicate and should be implemented differently
async def db_job_add_dynamic_children(job_id: CMJobID, children, returned_by, db: Storage):
    job = await get_job2(job_id, db)
    if not returned_by in job.children:
        msg = f"{job_id!r} does not know it has child  {returned_by!r}"
        raise CompmakeBug(msg)

    job.children.update(children)
    job.dynamic_children[returned_by] = children
    await set_job(job_id, job, db)
    job2 = await get_job2(job_id, db)
    assert job2.children == job.children, "Race condition"
    assert job2.dynamic_children == job.dynamic_children, "Race condition"


async def db_job_add_parent(db, job_id, parent):
    j = await get_job2(job_id, db)
    # print('%s old parents list: %s' % (d, j.parents))
    j.parents.add(parent)
    await set_job(job_id, j, db)
    j2 = await get_job2(job_id, db)
    assert j2.parents == j.parents, "Race condition"  # FIXME


async def db_job_add_parent_relation(child: CMJobID, parent: CMJobID, db: Storage):
    child_comp = await get_job2(child, db=db)
    orig = set(child_comp.parents)
    want = orig | {parent}
    # alright, need to take care of race condition
    while True:
        # Try to write
        child_comp.parents = want
        await set_job(child, child_comp, db=db)
        # now read back
        child_comp = await get_job2(child, db=db)
        if child_comp.parents != want:
            print(f"race condition for parents of {child}")
            print(f"orig: {orig}")
            print(f"want: {want}")
            print(f"now: {child_comp.parents}")
            # add the children of the other racers as well
            want = want | child_comp.parents
        else:
            break
