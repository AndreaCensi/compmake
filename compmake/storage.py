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
    return string2object(s)

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
def get_redis():
    global redis
    if redis is None:
        redis = Redis()
    return redis

