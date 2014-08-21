'''
These are all wrappers around the raw methods in storage
'''

from ..structures import Cache, CompmakeException, Job
from ..utils import wildcard_to_regexp
from contracts import contract



def remove_all_jobs(db):
    for job_id in all_jobs(db=db):
        delete_job(job_id=job_id, db=db)


def job2key(job_id):
    prefix = 'cm-job-'
    return '%s%s' % (prefix, job_id)


def key2job(key):
    prefix = 'cm-job-' 
    return key.replace(prefix, '', 1)
 

def all_jobs(db, force_db=False):  # @UnusedVariable
    ''' Returns the list of all jobs.
        If force_db is True, read jobs from DB.
        Otherwise, use local cache.
     '''
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


def set_job(job_id, computation, db):
    # TODO: check if they changed
    key = job2key(job_id)
    assert(isinstance(computation, Job))
    db[key] = computation


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
            assert(isinstance(cache, Cache))
        except Exception as e:
            del db[cache_key]
            # also remove user object?
            msg = 'Could not read Cache object for job "%s": %s; deleted.' % (job_id, e)
            raise CompmakeException(msg)
        return cache
    else:
        # make sure this is a valid job_id
        # XXX expensive
        # known = all_jobs()
        # if not job_id in known:
        #     raise CompmakeException("invalid job %s, I know %s" 
        # % (job_id, known)) 
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
    assert(isinstance(cache, Cache))
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

def get_job_userobject(job_id, db):
    key = job2userobjectkey(job_id)
    return db[key]

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
    args = dict(job_id=job_id, db=db)
    if job_exists(**args):
        delete_job(**args)
    if job_args_exists(**args):
        delete_job_args(**args)
    if job_userobject_exists(**args):
        delete_job_userobject(**args)
    if job_cache_exists(**args):
        delete_job_cache(**args)
