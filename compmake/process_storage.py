'''
Compmake stores three kind of data:

    1) Cache
    2) user_object
    3) tmp_object
   
These are all wrappers around the raw methods in storage
'''

from compmake.structures import Cache, Computation
from compmake.storage import db
#\
#    db.get_cache, db.delete_cache, db.is_cache_available, db.set_cache, redb.set_cache


### Cache 
def get_job_cache(job_id):
    cache_key = '%s:cache' % job_id
    if db.is_cache_available(cache_key):
        cache = db.get_cache(cache_key)
        assert(isinstance(cache, Cache))
        return cache
    else:
        computation = Computation.id2computations[job_id]
        cache = Cache(Cache.NOT_STARTED, computation)
        # we only put it later: NOT_STARTEd == not existent
        # db.set_cache(cache_key, cache)
        return cache 

def set_job_cache(job_id, cache):
    assert(isinstance(cache, Cache))
    cache_key = '%s:cache' % job_id
    db.set_cache(cache_key, cache)
    
def delete_job_cache(job_id):
    cache_key = '%s:cache' % job_id
    db.delete_cache(cache_key)
    
    
#### User objects
def get_job_userobject(job_id):
    assert(is_job_userobject_available(job_id))
    key = '%s:userobject' % job_id
    return db.get_cache(key)

def is_job_userobject_available(job_id):
    key = '%s:userobject' % job_id
    return db.is_cache_available(key)

def set_job_userobject(job_id, obj):
    key = '%s:userobject' % job_id
    db.set_cache(key, obj)
    
def delete_job_userobject(job_id):
    key = '%s:userobject' % job_id
    db.delete_cache(key)
    
#### Temporary objects
def get_job_tmpobject(job_id):
    assert(is_job_tmpobject_available(job_id))
    key = '%s:userobject:tmp' % job_id
    return db.get_cache(key)

def is_job_tmpobject_available(job_id):
    key = '%s:userobject:tmp' % job_id
    return db.is_cache_available(key)

def set_job_tmpobject(job_id, obj):
    key = '%s:userobject:tmp' % job_id
    db.set_cache(key, obj)
    
def delete_job_tmpobject(job_id):
    key = '%s:userobject:tmp' % job_id
    db.delete_cache(key)

