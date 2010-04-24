'''
Compmake stores three kind of data:

    1) Cache
    2) user_object
    3) tmp_object
   
These are all wrappers around the raw methods in storage
'''

from compmake.structures import Cache, Computation
from compmake.storage import \
    get_cache, delete_cache, is_cache_available, set_cache, reset_cache


### Cache 
def get_job_cache(job_id):
    cache_key = '%s:cache' % job_id
    if is_cache_available(cache_key):
        cache = get_cache(cache_key)
        assert(isinstance(cache, Cache))
        return cache
    else:
        computation = Computation.id2computations[job_id]
        cache = Cache(Cache.NOT_STARTED, computation)
        # we only put it later: NOT_STARTEd == not existent
        # set_cache(cache_key, cache)
        return cache 

def set_job_cache(job_id, cache):
    assert(isinstance(cache, Cache))
    cache_key = '%s:cache' % job_id
    set_cache(cache_key, cache)
    
def delete_job_cache(job_id):
    cache_key = '%s:cache' % job_id
    delete_cache(cache_key)
    
    
#### User objects
def get_job_userobject(job_id):
    assert(is_job_userobject_available(job_id))
    key = '%s:userobject' % job_id
    return get_cache(key)

def is_job_userobject_available(job_id):
    key = '%s:userobject' % job_id
    return is_cache_available(key)

def set_job_userobject(job_id, obj):
    key = '%s:userobject' % job_id
    set_cache(key, obj)
    
def delete_job_userobject(job_id):
    key = '%s:userobject' % job_id
    delete_cache(key)
    
#### Temporary objects
def get_job_tmpobject(job_id):
    assert(is_job_tmpobject_available(job_id))
    key = '%s:userobject:tmp' % job_id
    return get_cache(key)

def is_job_tmpobject_available(job_id):
    key = '%s:userobject:tmp' % job_id
    return is_cache_available(key)

def set_job_tmpobject(job_id, obj):
    key = '%s:userobject:tmp' % job_id
    set_cache(key, obj)
    
def delete_job_tmpobject(job_id):
    key = '%s:userobject:tmp' % job_id
    delete_cache(key)

