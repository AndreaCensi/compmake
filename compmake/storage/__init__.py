from .. import CompmakeGlobalState, get_compmake_config
from ..ui import info
from .filesystem import StorageFilesystem
import os

#
#def use_redis(host=None, port=None):
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


def use_filesystem(directory=None):
    if directory is None:
        directory = get_compmake_config('path')
    directory = os.path.expandvars(directory)
    directory = os.path.expanduser(directory)
    CompmakeGlobalState.db = StorageFilesystem(directory)


