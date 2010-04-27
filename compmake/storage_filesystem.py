import os 
import pickle
from glob import glob
from os import makedirs
from os.path import expanduser, dirname, join, expandvars, \
    splitext, exists, basename
from StringIO import StringIO

from compmake.structures import ParsimException 

class StorageFilesystem:
    basepath = '~/compmake'
    
    local_cache = {}
    
    @staticmethod
    def __str__():
        return "Filesystem backend"
    
    @staticmethod
    def supports_concurrency():
        return False
    
    @staticmethod
    def get_cache(key):
        if not StorageFilesystem.is_cache_available(key):
            raise ParsimException('Could not find job %s' % key)
        filename = filename_for_key(key)
        try:
            file = open(filename, 'r')
            content = file.read()
            file.close()
            # print "R %s len %d" % (key, len(content))
            sio = StringIO(content)
            state = pickle.load(sio)
            return state
        except EOFError:
            raise  EOFError("Could not unpickle file %s" % file) 
    
    @staticmethod
    def delete_cache(key):
        filename = filename_for_key(key)
        assert(os.path.exists(filename))
        os.remove(filename)
        
    @staticmethod
    def is_cache_available(key):  
        filename = filename_for_key(key)
        return exists(filename)
    
    @staticmethod
    def set_cache(key, value, precious=False):
        filename = filename_for_key(key)
        
        sio = StringIO()
        pickle.dump(value, sio, pickle.HIGHEST_PROTOCOL)
        content = sio.getvalue()
    
        file = open(filename, 'w')
        file.write(content)
        file.flush()
        os.fsync(file) # XXX I'm desperate
        file.close()
        
        if precious:
            StorageFilesystem.local_cache[key] = value
    
    #@staticmethod   
    #def reset_cache():
     #   raise TypeError
        #""" reset the whole cache """
        #keys = get_redis().keys(pattern = key2rediskey('*') ).split()
        #for k in keys:
        #    res = get_redis().delete(k)
        # return keys
    
    @staticmethod
    # TODO change key
    def keys(pattern):
        filename = filename_for_key(pattern)
        basekeys = [ splitext(basename(x))[0] for x in glob(filename)]
        return basekeys
    

def key2filename(key):
    '''turns a key into a reasonable filename'''
    key = key.replace('/', '|')
    key = key.replace('.', 'D')
    key = key.replace('~', 'HOME')
    return key

def get_computations_root():  
    basepath = expandvars(expanduser(StorageFilesystem.basepath))
    return basepath

def filename_for_key(key):
    """ Returns the pickle storage filename corresponding to the job id """
    filename =  join(get_computations_root(), key2filename(key) + '.pickle')
    directory = dirname(filename)
    if not exists(directory):
        makedirs(directory)
    return filename
