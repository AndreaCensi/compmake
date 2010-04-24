import os, sys, fcntl
import pickle

from StringIO import StringIO
from redis import Redis

from compmake.structures import ParsimException, Computation


class RedisInterface:
    host = 'localhost'
    port = 6379
    
    # XXX Add dbname
    local_cache = {}
    
    @staticmethod
    def __str__():
        return "Redis backend"
    
    @staticmethod
    def supports_concurrency():
        return True
        
    # Storage public interface
    @staticmethod
    def get_cache(name):
        #
        if RedisInterface.local_cache.has_key(name):
            sys.stderr.write('+')
            return RedisInterface.local_cache[name]
        
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
    
        # Useful to get a sense what it's doing
        # sys.stderr.write('Load %s [%.2fK]\n' % (name, len(s)/1000.0 ) )
        return value
    
    @staticmethod
    def delete_cache(name):
        k = key2rediskey(name)
        get_redis().delete(k)
        
    @staticmethod
    def is_cache_available(name):
        k = key2rediskey(name)
        return get_redis().exists(k)
    
    @staticmethod
    def set_cache(name, value, precious=False):
        k = key2rediskey(name)
        s = object2string(value)
        
        # Useful to get a sense what it's doing
        # sys.stderr.write('Save %s [%.2fK]\n' % (name, len(s)/1000.0 ) )
        
        get_redis().set(k, s)
        
        if precious:
            RedisInterface.local_cache[name] = value
 
    @staticmethod
    def keys(pattern='*'):
        K = get_redis().keys(pattern = key2rediskey(pattern) )
        assert(isinstance(K, str))
        K = K.split()
        assert(isinstance(K, list))
        return [rediskey2key(k) for k in K]
    
#    @staticmethod   
#    def reset_cache():
#        """ reset the whole cache """
#        keys = get_redis().keys(pattern = key2rediskey('*') ).split()
#        for k in keys:
#            res = get_redis().delete(k)
#        return keys

# Other utilities

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

def rediskey2key(key):
    return key.replace('compmake:','',1)

redis = None

def get_redis():
    global redis
    if redis is None:
        # sys.stderr.write("Opening connection to Redis (host=%s)... " % redis_host)
        redis = Redis(host=RedisInterface.host,port=RedisInterface.port)
        # sys.stderr.write("done.\n")
    return redis