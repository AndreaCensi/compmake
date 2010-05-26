import os
from compmake.utils.visualization import info
from compmake.config import compmake_config

db = None

def use_redis(host=None, port=None):
    if host is None:
        host = 'localhost'
    if port is None:
        port = 6379
        
    from compmake.storage.redisdb import RedisInterface, get_redis
    global db
    db = RedisInterface
    db.host = host
    db.port = int(port)
    
    get_redis()

def use_filesystem(directory=None):
    if directory is None:
        directory = compmake_config.path #@UndefinedVariable
        
    from compmake.storage.filesystem import StorageFilesystem
    global db
    db = StorageFilesystem
    db.basepath = directory
    
    if not os.path.exists(directory):
        info("Creating storage directory %s" % directory)
        os.makedirs(directory)

#use_redis()
use_filesystem()

