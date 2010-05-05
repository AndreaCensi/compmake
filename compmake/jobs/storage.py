'''
Compmake stores 4 kind of data, all of them indexed by a job_id string.

    1) Computation objects
    2) Cache objects.
    3) user_object (any type)
    4) tmp_object (any type)

These are all wrappers around the raw methods in storage
'''

from compmake.structures import Cache, Computation
from compmake import storage

namespace = 'default'

def remove_all_jobs():
    map(remove_computation, all_jobs())
    
def job2key(job_id):
    prefix = 'compmake:%s:job:' % namespace
    return '%s%s' % (prefix, job_id) 

def key2job(key):
    prefix = 'compmake:%s:job:' % namespace
    return key.replace(prefix, '', 1)

def all_jobs():
    ''' Returns the list of all jobs '''
    # XXX we should check we don't return subsidiaries
    keys = storage.db.keys(job2key('*'))
    return map(key2job, keys)
    #return Computation.id2computation.keys()

def get_computation(job_id):
    key = job2key(job_id)
    computation = storage.db.get_cache(key)
    assert(isinstance(computation, Computation))
    return computation
    #return Computation.id2computation[job_id]

def exists_computation(job_id):
    key = job2key(job_id)
    return storage.db.is_cache_available(key)
    #return job_id in Computation.id2computation

def set_computation(job_id, computation):
    # TODO: check if they changed
    key = job2key(job_id)
    assert(isinstance(computation, Computation))
   # Computation.id2computation[job_id] = computation
    storage.db.set_cache(key, computation)
        
def remove_computation(job_id):
    key = job2key(job_id)
    storage.db.delete_cache(key)

#
# Cache objects
#
def get_job_cache(job_id):
    cache_key = '%s:cache' % job_id
    if storage.db.is_cache_available(cache_key):
        cache = storage.db.get_cache(cache_key)
        assert(isinstance(cache, Cache))
        return cache
    else:
        # make sure this is a valid job_id
        assert(job_id in all_jobs()) 
        #computation = Computation.id2computations[job_id]
        cache = Cache(Cache.NOT_STARTED)
        # we only put it later: NOT_STARTEd == not existent
        # storage.db.set_cache(cache_key, cache)
        return cache 

def set_job_cache(job_id, cache):
    assert(isinstance(cache, Cache))
    cache_key = '%s:cache' % job_id
    storage.db.set_cache(cache_key, cache)
    
def delete_job_cache(job_id):
    cache_key = '%s:cache' % job_id
    storage.db.delete_cache(cache_key)
    
#
# User objects
#
def get_job_userobject(job_id):
    assert(is_job_userobject_available(job_id))
    key = '%s:userobject' % job_id
    return storage.db.get_cache(key)

def is_job_userobject_available(job_id):
    key = '%s:userobject' % job_id
    return storage.db.is_cache_available(key)

def set_job_userobject(job_id, obj):
    key = '%s:userobject' % job_id
    storage.db.set_cache(key, obj)
    
def delete_job_userobject(job_id):
    key = '%s:userobject' % job_id
    storage.db.delete_cache(key)
    
#
# Temporary objects
#

# TODO: add function 2key

def get_job_tmpobject(job_id):
    assert(is_job_tmpobject_available(job_id))
    key = '%s:userobject:tmp' % job_id
    return storage.db.get_cache(key)

def is_job_tmpobject_available(job_id):
    key = '%s:userobject:tmp' % job_id
    return storage.db.is_cache_available(key)

def set_job_tmpobject(job_id, obj):
    key = '%s:userobject:tmp' % job_id
    storage.db.set_cache(key, obj)
    
def delete_job_tmpobject(job_id):
    key = '%s:userobject:tmp' % job_id
    storage.db.delete_cache(key)

