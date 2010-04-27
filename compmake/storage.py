import os

db = None
print "initialized to None again"

def use_redis(host=None,port=None):
    if host is None:
        host = 'localhost'
    if port is None:
        port = 6379
        
    from compmake.storage_redis import RedisInterface
    global db
    db = RedisInterface
    db.host = host
    db.port = port

def use_filesystem(directory=None):
    print __name__
    if directory is None:
        directory = 'compmake_storage'
        
    from compmake.storage_filesystem import StorageFilesystem
    global db
    db = StorageFilesystem
    db.basepath = directory
    
    if not os.path.exists(directory):
        print "Creating storage directory %s" % directory
        os.makedirs(directory)

#use_filesystem()
#use_redis()


