
from .filesystem import StorageFilesystem
from .memorycache import MemoryCache


#
# def use_redis(host=None, port=None):
#    if host is None:
#        host = 'localhost'
#    if port is None:
#        port = 6379
#    else:
#        port = int(port)
#
#    from .redisdb import RedisInterface, get_redis
#    from .. import CompmakeGlobalState
#    # XXX: make class instance
#    CompmakeGlobalState.db = RedisInterface
#    CompmakeGlobalState.db.host = host
#    CompmakeGlobalState.db.port = port
#    get_redis()
 