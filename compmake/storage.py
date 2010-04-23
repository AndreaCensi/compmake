import os, sys, fcntl
import pickle

from StringIO import StringIO
from redis import Redis

from compmake.structures import ParsimException
from compmake.structures import Computation

local_cache = {}

# TODO add should_be_fast

# Storage public interface
def get_cache(name):
    global local_cache
    if local_cache.has_key(name):
        sys.stderr.write('+')
        return local_cache[name]
    
    k = key2rediskey(name)
    s = get_redis().get(k)
    try:
        value = string2object(s)
    except Exception as e:
        tmp_core = '/tmp/pickle_core' 
        open(tmp_core,'w').write(s)
        msg = "Could not load cache %s. Dumped %s. Error: %s" % (name, tmp_core, e)
        print msg
        raise e

   # local_cache[name] = value
    sys.stderr.write('Load %s [%dK]\n' % (name, len(s)/1000 ) )
    return value

def delete_cache(name):
    k = key2rediskey(name)
    get_redis().delete(k)
    
def is_cache_available(name):
    k = key2rediskey(name)
    return get_redis().exists(k)
    
def set_cache(name, value, precious=False):
    k = key2rediskey(name)
    s = object2string(value)
    get_redis().set(k, s)
    
    if precious:
        global local_cache
        local_cache[name] = value
    
def reset_cache():
    """ reset the whole cache """
    keys = get_redis().keys(pattern = key2rediskey('*') ).split()
    for k in keys:
        res = get_redis().delete(k)
    return keys

# Serialization device
def object2string(obj):
    sio = StringIO()
    pickle.dump(obj, sio, pickle.HIGHEST_PROTOCOL)
    return sio.getvalue()

def string2object(s):
    sio = StringIO(s)
    return pickle.load(sio)

# 
def key2rediskey(s):
    return "compmake:%s" % s

redis = None
redis_host = 'localhost'
def get_redis():
    global redis
    if redis is None:
        sys.stderr.write("Opening connection to Redis (host=%s)... " % redis_host)
        redis = Redis(host=redis_host)
        sys.stderr.write("done.\n")
    return redis

