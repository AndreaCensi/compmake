import os, sys, fcntl
import pickle

from StringIO import StringIO
from redis import Redis

from compmake.structures import ParsimException
from compmake.structures import Computation

# Storage public interface
def get_cache(name):
    k = key2rediskey(name)
    s = get_redis().get(k)
    try:
        ob = string2object(s)
    except:
        tmp_core = '/tmp/pickle_core' 
        open(tmp_core,'w').write(s)
        print "Could not load cache %s. Dumped %s" % (name, tmp_core)

def delete_cache(name):
    k = key2rediskey(name)
    get_redis().delete(k)
    
def is_cache_available(name):
    k = key2rediskey(name)
    return get_redis().exists(k)
    
def set_cache(name, value):
    k = key2rediskey(name)
    s = object2string(value)
    get_redis().set(k, s)
    
def reset_cache():
    """ reset the whole cache """
    keys = get_redis().keys(pattern = key2rediskey('*') ).split()
    for k in keys:
        res = get_redis().delete(k)
    return keys

# Serialization device
def object2string(obj):
    sio = StringIO()
    pickle.dump(obj, sio)
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

