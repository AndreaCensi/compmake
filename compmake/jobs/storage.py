'''
Compmake stores 4 kind of data, all of them indexed by a job_id string.

    1) Computation objects
    2) Cache objects.
    3) user_object (any type)
    4) tmp_object (any type)
   
Object of type (1) are kept in memory, while objects of type (2-4) 
are kept in the database (using storage_db).

The storage/index for objects in type (1) is the dict Computation.id2computations

These are all wrappers around the raw methods in storage
'''

from compmake.structures import Cache, Computation
from compmake import storage

def all_jobs():
    ''' Returns the list of all jobs '''
    return Computation.id2computation.keys()

def get_computation(job_id):
    return Computation.id2computation[job_id]

def exists_computation(job_id):
    return job_id in Computation.id2computation.keys()

def add_computation(job_id, computation):
    assert(isinstance(computation, Computation))
    Computation.id2computation[job_id] = computation
        

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

