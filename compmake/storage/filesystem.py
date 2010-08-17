import os 
import pickle
from glob import glob
from os import makedirs
from os.path import expanduser, dirname, join, expandvars, \
    splitext, exists, basename
from StringIO import StringIO

from compmake.structures import CompmakeException , SerializationError

def try_to_unpickle_string(s):
    ''' Tries to unpickle the string, raises an exception if not possible.'''
  #  try:
    sio = StringIO(s)
    state = pickle.load(sio)
    return state
#    except Exception, e:
 #       raise CompmakeException("Could not unpickle string")


class StorageFilesystem:
    basepath = '~/compmake'
    
    @staticmethod
    def __str__():
        return "Filesystem backend"
    
    @staticmethod
    def supports_concurrency():
        return False
    
    @staticmethod
    def get(key):
        if not StorageFilesystem.exists(key):
            raise CompmakeException('Could not find job %s' % key)
        filename = StorageFilesystem.filename_for_key(key)
        try:
            file = open(filename, 'r')
            content = file.read()
            file.close()
            # print "R %s len %d" % (key, len(content))
            sio = StringIO(content)
            state = pickle.load(sio)
            return state
        except Exception, e:
            raise CompmakeException("Could not unpickle file %s (%s)" % (filename, e)) 
    
    @staticmethod
    def delete(key):
        filename = StorageFilesystem.filename_for_key(key)
        assert os.path.exists(filename), \
            'I expected path %s to exist before deleting' % filename
        os.remove(filename)
        
    @staticmethod
    def exists(key):  
        filename = StorageFilesystem.filename_for_key(key)
        it_is = exists(filename)
#        if not it_is:
#            print "File %s not found" % filename
        return it_is
    
    @staticmethod
    def set(key, value):
        filename = StorageFilesystem.filename_for_key(key)
        
        sio = StringIO()
        try:
            pickle.dump(value, sio, pickle.HIGHEST_PROTOCOL)
        except Exception as e:
            raise SerializationError('Cannot set key %s: cannot pickle object '
                    'of class %s: %s' % (key, value.__class__.__name__, e))
        content = sio.getvalue()

        try:    
            try_to_unpickle_string(content)
        except Exception, e:
            raise Exception('Could not deserialize key %s: %s \n%s ' % (key, e, value))
            
    
        file = open(filename, 'w')
        file.write(content)
        file.flush()
        os.fsync(file) # XXX I'm desperate
        file.close()

    @staticmethod
    # TODO change key
    def keys(pattern):
        filename = StorageFilesystem.filename_for_key(pattern)
        basenames = [ splitext(basename(x))[0] for x in glob(filename)]
        return [StorageFilesystem.filename2key(b) for b in basenames]
    
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
        basepath = expandvars(expanduser(StorageFilesystem.basepath))
        filename = join(basepath, StorageFilesystem.key2filename(key) + '.pickle')
        directory = dirname(filename)
        if not exists(directory):
            makedirs(directory)
        return filename
