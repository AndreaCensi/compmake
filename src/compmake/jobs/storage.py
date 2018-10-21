# -*- coding: utf-8 -*-
"""
    These are all wrappers around the raw methods in storage
"""

from compmake.exceptions import CompmakeBug, CompmakeException, CompmakeDBError
from compmake.utils.pickle_frustration import pickle_main_context_load
from contracts import contract
from contracts.utils import raise_desc

from ..structures import Cache, Job
from ..utils import wildcard_to_regexp


def job2key(job_id):
    prefix = 'cm-job-'
    return '%s%s' % (prefix, job_id)


def key2job(key):
    prefix = 'cm-job-'
    return key.replace(prefix, '', 1)


def all_jobs(db, force_db=False):  # @UnusedVariable
    """ Returns the list of all jobs.
        If force_db is True, read jobs from DB.
        Otherwise, use local cache.
     """
    pattern = job2key('*')
    regexp = wildcard_to_regexp(pattern)

    for key in db.keys():
        if regexp.match(key):
            yield key2job(key)


def get_job(job_id, db):
    key = job2key(job_id)
    computation = db[key]
    assert isinstance(computation, Job)
    return computation


def job_exists(job_id, db):
    key = job2key(job_id)
    return key in db


def assert_job_exists(job_id, db):
    """
        :raise CompmakeBug: if the job does not exist
    """
    get_job(job_id, db)


def set_job(job_id, job, db):
    # TODO: check if they changed
    key = job2key(job_id)
    assert (isinstance(job, Job))
    db[key] = job


def delete_job(job_id, db):
    key = job2key(job_id)
    del db[key]


#
# Cache objects
#
def job2cachekey(job_id):
    prefix = 'cm-cache-'
    return '%s%s' % (prefix, job_id)


def get_job_cache(job_id, db):
    cache_key = job2cachekey(job_id)
    if cache_key in db:
        try:
            cache = db[cache_key]
            assert isinstance(cache, Cache)
        except Exception as e:
            del db[cache_key]
            # also remove user object?
            msg = 'Could not read Cache object for job "%s": %s; deleted.' % (
                job_id, e)
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
            raise_desc(CompmakeDBError,
                       'Requesting cache for job that does not exist.',
                       job_id=job_id)

        cache = Cache(Cache.NOT_STARTED)
        # we only put it later: NOT_STARTEd == not existent
        # get_compmake_db().set(cache_key, cache)
        return cache


def job_cache_exists(job_id, db):
    key = job2cachekey(job_id)
    return key in db


def job_cache_sizeof(job_id, db):
    key = job2cachekey(job_id)
    return db.sizeof(key)


def set_job_cache(job_id, cache, db):
    assert (isinstance(cache, Cache))
    key = job2cachekey(job_id)
    db[key] = cache


@contract(job_id=str)
def delete_job_cache(job_id, db):
    key = job2cachekey(job_id)
    del db[key]


#
# User objects
#
def job2userobjectkey(job_id):
    prefix = 'cm-res-'
    return '%s%s' % (prefix, job_id)

    # print('All deps: %r' % all_deps)


def get_job_userobject(job_id, db):
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


def job_userobject_sizeof(job_id, db):
    key = job2userobjectkey(job_id)
    return db.sizeof(key)


def is_job_userobject_available(job_id, db):
    key = job2userobjectkey(job_id)
    return key in db


job_userobject_exists = is_job_userobject_available


def set_job_userobject(job_id, obj, db):
    key = job2userobjectkey(job_id)
    db[key] = obj


def delete_job_userobject(job_id, db):
    key = job2userobjectkey(job_id)
    del db[key]


def job2jobargskey(job_id):
    prefix = 'cm-args-'
    return '%s%s' % (prefix, job_id)


def get_job_args(job_id, db):
    key = job2jobargskey(job_id)

    if False:
        return db[key]
    else:
        job = get_job(job_id, db)
        pickle_main_context = job.pickle_main_context
        with pickle_main_context_load(pickle_main_context):
            return db[key]


def job_args_exists(job_id, db):
    key = job2jobargskey(job_id)
    return key in db


def job_args_sizeof(job_id, db):
    key = job2jobargskey(job_id)
    return db.sizeof(key)


def set_job_args(job_id, obj, db):
    key = job2jobargskey(job_id)
    db[key] = obj


def delete_job_args(job_id, db):
    key = job2jobargskey(job_id)
    del db[key]


def delete_all_job_data(job_id, db):
    # print('deleting_all_job_data(%r)' % job_id)
    args = dict(job_id=job_id, db=db)
    if job_exists(**args):
        delete_job(**args)
    if job_args_exists(**args):
        delete_job_args(**args)
    if job_userobject_exists(**args):
        delete_job_userobject(**args)
    if job_cache_exists(**args):
        delete_job_cache(**args)


# These are delicate and should be implemented differently
def db_job_add_dynamic_children(job_id, children, returned_by, db):
    job = get_job(job_id, db)
    if not returned_by in job.children:
        msg = '%r does not know it has child  %r' % (job_id, returned_by)
        raise CompmakeBug(msg)

    job.children.update(children)
    job.dynamic_children[returned_by] = children
    set_job(job_id, job, db)
    job2 = get_job(job_id, db)
    assert job2.children == job.children, 'Race condition'
    assert job2.dynamic_children == job.dynamic_children, 'Race condition'


def db_job_add_parent(db, job_id, parent):
    j = get_job(job_id, db)
    # print('%s old parents list: %s' % (d, j.parents))
    j.parents.add(parent)
    set_job(job_id, j, db)
    j2 = get_job(job_id, db)
    assert j2.parents == j.parents, 'Race condition'  # FIXME


def db_job_add_parent_relation(child, parent, db):
    child_comp = get_job(child, db=db)
    orig = set(child_comp.parents)
    want = orig | set([parent])
    # alright, need to take care of race condition
    while True:
        # Try to write
        child_comp.parents = want
        set_job(child, child_comp, db=db)
        # now read back
        child_comp = get_job(child, db=db)
        if child_comp.parents != want:
            print('race condition for parents of %s' % child)
            print('orig: %s' % orig)
            print('want: %s' % want)
            print('now: %s' % child_comp.parents)
            # add the children of the other racers as well
            want = want | child_comp.parents
        else:
            break
