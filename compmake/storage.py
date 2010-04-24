
db = None

def use_redis(host='localhost',port=6379):
    from compmake.storage_redis import RedisInterface
    global db
    db = RedisInterface
    db.host = host
    db.port = port

def use_filesystem(directory='~/compmake'):
    from compmake.storage_filesystem import StorageFilesystem
    global db
    db = StorageFilesystem
    db.basepath = directory

#use_filesystem()
use_redis()


