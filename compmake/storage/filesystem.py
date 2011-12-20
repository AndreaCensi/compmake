from ..structures import CompmakeException, SerializationError
from StringIO import StringIO
from glob import glob
from os.path import splitext, basename
import cPickle as pickle
import os
import time


PRINT_STATS = False


def print_stats(method, key, length, duration):
    print("stats: %10s  %8d bytes  %.2fs %s" % (method, length, duration, key))


class StorageFilesystem:
    basepath = 'compmake_storage'
    checked_existence = False
    
    @staticmethod
    def __str__():
        return "Filesystem backend"
    
    @staticmethod
    def supports_concurrency():
        return False
    
    @staticmethod
    def get(key):
        if not StorageFilesystem.exists(key):
            raise CompmakeException('Could not find key %r.' % key)
        filename = StorageFilesystem.filename_for_key(key)
        try:
            start = time.time()
            file = open(filename, 'rb')  # @ReservedAssignment
            content = file.read()
            file.close()
            # print "R %s len %d" % (key, len(content))
            sio = StringIO(content)
            state = pickle.load(sio)
            
            duration = time.time() - start
            if PRINT_STATS:
                length = len(content)
                print_stats('get    ', key, length, duration)
            return state
        except Exception as e:
            msg = "Could not unpickle file %r: %s" % (filename, e)
            raise CompmakeException(msg) 
        
    @staticmethod
    def set(key, value):  # @ReservedAssignment
        if not StorageFilesystem.checked_existence:
            StorageFilesystem.checked_existence = True
            if not os.path.exists(StorageFilesystem.basepath):
                os.makedirs(StorageFilesystem.basepath)
            
        filename = StorageFilesystem.filename_for_key(key)
        start = time.time()
        
        sio = StringIO()
        try:
            pickle.dump(value, sio, pickle.HIGHEST_PROTOCOL)
        except Exception as e:
            raise SerializationError('Cannot set key %s: cannot pickle object '
                    'of class %s: %s' % (key, value.__class__.__name__, e))
        
        content = sio.getvalue()
        with open(filename, 'wb') as f:
            f.write(content)

        duration = time.time() - start
        if PRINT_STATS:
            length = len(content)
            print_stats('    set', key, length, duration)
        
    @staticmethod
    def delete(key):
        filename = StorageFilesystem.filename_for_key(key)
        assert os.path.exists(filename), \
            'I expected path %s to exist before deleting' % filename
        os.remove(filename)
        
    @staticmethod
    def exists(key):  
        filename = StorageFilesystem.filename_for_key(key)
        return os.path.exists(filename)

    @staticmethod
    # TODO change key
    def keys(pattern):
        filename = StorageFilesystem.filename_for_key(pattern)
        for x in glob(filename):
            b = splitext(basename(x))[0]
            yield StorageFilesystem.filename2key(b)

    @staticmethod
    def reopen_after_fork():
        pass
    
    dangerous_chars = {
       '/': 'CMSLASH',
       '..': 'CMDOT',
       '~': 'CMHOME'
    }
    
    @staticmethod
    def key2filename(key):
        '''turns a key into a reasonable filename'''
        for char, replacement in StorageFilesystem.dangerous_chars.items():
            key = key.replace(char, replacement)
        return key
    
    @staticmethod
    def filename2key(key):
        ''' Undoes key2filename '''
        for char, replacement in StorageFilesystem.dangerous_chars.items():
            key = key.replace(replacement, char)
        return key
    
    @staticmethod
    def filename_for_key(key):
        """ Returns the pickle storage filename corresponding to the job id """
        return os.path.join(StorageFilesystem.basepath,
                            StorageFilesystem.key2filename(key) + '.pickle')
        
