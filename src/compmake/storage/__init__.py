from .filesystem import StorageFilesystem
from .filesystem2 import StorageFilesystem2
from .memorycache import MemoryCache
from compmake import get_compmake_config, logger, CompmakeGlobalState
from compmake.state import set_compmake_db
from compmake.ui import info
import os

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


def use_filesystem(directory=None):
    db = CompmakeGlobalState.compmake_db 
        
    
    if directory is None:
        directory = get_compmake_config('path')
    
    if db is not None:
        if isinstance(db, StorageFilesystem):
            # logger.warning('Switching from db %r to %r' % (db, directory))
            pass
#            raise ValueError() # TMP

    directory = os.path.expandvars(directory)
    directory = os.path.expanduser(directory)
    
    sf = StorageFilesystem(directory)
#     sf = StorageFilesystem2(directory)
#     sf = MemoryCache(sf)
    set_compmake_db(sf)


