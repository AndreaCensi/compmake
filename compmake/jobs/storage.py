'''
Compmake stores 4 kind of data, all of them indexed by a job_id string.

    1) Job objects
    2) Cache objects.
    3) user_object (any type)
    4) tmp_object (any type)

These are all wrappers around the raw methods in storage
'''
from .. import CompmakeGlobalState
from ..structures import Cache, Job, CompmakeException
from ..ui import  info


def set_namespace(n):
    if n != 'default':
        info('Using namespace %r.' % n)
    CompmakeGlobalState.namespace = n


def get_namespace():
    return CompmakeGlobalState.namespace


def remove_all_jobs():
    map(delete_job, all_jobs())


def job2key(job_id):
    prefix = 'compmake:%s:job:' % get_namespace()
    return '%s%s' % (prefix, job_id)


def key2job(key):
    prefix = 'compmake:%s:job:' % get_namespace()
    return key.replace(prefix, '', 1)


def all_jobs(force_db=False): #@UnusedVariable
    ''' Returns the list of all jobs.
        If force_db is True, read jobs from DB.
        Otherwise, use local cache.
     '''
#    if force_db:
        # XXX we should check we don't return subsidiaries
    for key in CompmakeGlobalState.db.keys(job2key('*')): #@UndefinedVariable
        yield key2job(key)
#    else:
        # XXX FIXME does not work when compmake is called by itself
#        from compmake.ui.ui import jobs_defined_in_this_session

#        for job in jobs_defined_in_this_session:
#            yield job 


def get_job(job_id):
    key = job2key(job_id)
    computation = CompmakeGlobalState.db.get(key)
    assert(isinstance(computation, Job))
    return computation


def job_exists(job_id):
    key = job2key(job_id)
    return CompmakeGlobalState.db.exists(key)


def set_job(job_id, computation):
    # TODO: check if they changed
    key = job2key(job_id)
    assert(isinstance(computation, Job))
    CompmakeGlobalState.db.set(key, computation)


def delete_job(job_id):
    key = job2key(job_id)
    CompmakeGlobalState.db.delete(key)


#
# Cache objects
#
def job2cachekey(job_id):
    prefix = 'compmake:%s:cache:' % get_namespace()
    return '%s%s' % (prefix, job_id)


def get_job_cache(job_id):
    cache_key = job2cachekey(job_id)
    if CompmakeGlobalState.db.exists(cache_key):
        try:
            cache = CompmakeGlobalState.db.get(cache_key)
            assert(isinstance(cache, Cache))
        except Exception as e:
            CompmakeGlobalState.db.delete(cache_key)
            # also remove user object?
            raise CompmakeException('Could not read Cache object for job "%s":'
                                    ' %s; deleted.' % (job_id, e))
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
        # CompmakeGlobalState.db.set(cache_key, cache)
        return cache


def set_job_cache(job_id, cache):
    assert(isinstance(cache, Cache))
    cache_key = job2cachekey(job_id)
    CompmakeGlobalState.db.set(cache_key, cache)


def delete_job_cache(job_id):
    cache_key = job2cachekey(job_id)
    CompmakeGlobalState.db.delete(cache_key)


#
# User objects
#
def job2userobjectkey(job_id):
    prefix = 'compmake:%s:userobject:' % get_namespace()
    return '%s%s' % (prefix, job_id)


def get_job_userobject(job_id):
    assert(is_job_userobject_available(job_id))
    key = job2userobjectkey(job_id)
    return CompmakeGlobalState.db.get(key)


def is_job_userobject_available(job_id):
    key = job2userobjectkey(job_id)
    return CompmakeGlobalState.db.exists(key)


def set_job_userobject(job_id, obj):
    key = job2userobjectkey(job_id)
    CompmakeGlobalState.db.set(key, obj)


def delete_job_userobject(job_id):
    key = job2userobjectkey(job_id)
    CompmakeGlobalState.db.delete(key)

#
# Temporary objects
#


# TODO: add function 2key
def job2tmpobjectkey(job_id):
    prefix = 'compmake:%s:tmpobject:' % get_namespace()
    return '%s%s' % (prefix, job_id)


def get_job_tmpobject(job_id):
    assert(is_job_tmpobject_available(job_id))
    key = job2tmpobjectkey(job_id)
    return CompmakeGlobalState.db.get(key)


def is_job_tmpobject_available(job_id):
    key = job2tmpobjectkey(job_id)
    return CompmakeGlobalState.db.exists(key)


def set_job_tmpobject(job_id, obj):
    key = job2tmpobjectkey(job_id)
    CompmakeGlobalState.db.set(key, obj)


def delete_job_tmpobject(job_id):
    key = job2tmpobjectkey(job_id)
    CompmakeGlobalState.db.delete(key)


def job2jobargskey(job_id):
    prefix = 'compmake:%s:jobargs:' % get_namespace()
    return '%s%s' % (prefix, job_id)


def get_job_args(job_id):
    assert job_args_exists(job_id)
    key = job2jobargskey(job_id)
    return CompmakeGlobalState.db.get(key)


def job_args_exists(job_id):
    key = job2jobargskey(job_id)
    return CompmakeGlobalState.db.exists(key)


def set_job_args(job_id, obj):
    key = job2jobargskey(job_id)
    CompmakeGlobalState.db.set(key, obj)


def delete_job_args(job_id):
    key = job2jobargskey(job_id)
    CompmakeGlobalState.db.delete(key)
