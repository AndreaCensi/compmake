from ..structures import CompmakeException, SerializationError
from ..utils import find_pickling_error, safe_write
from StringIO import StringIO
from glob import glob
from os.path import splitext, basename
import cPickle
import os

pickle = cPickle

if True:
    track_time = lambda x: x
else:
    from ..utils import TimeTrack
    track_time = TimeTrack.decorator

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
    @track_time
    def get(key):
        if not StorageFilesystem.exists(key):
            raise CompmakeException('Could not find key %r.' % key)
        filename = StorageFilesystem.filename_for_key(key)
        try:
            if False:
                file = open(filename, 'rb')  # @ReservedAssignment
                content = file.read()
                file.close()
                # print "R %s len %d" % (key, len(content))
                sio = StringIO(content)
                state = pickle.load(sio)
                return state
            else:
                with open(filename, 'rb') as f:
                    return pickle.load(f)
        except Exception as e:
            msg = "Could not unpickle file %r: %s" % (filename, e)
            raise CompmakeException(msg)

    @staticmethod
    @track_time
    def set(key, value):  # @ReservedAssignment
        if not StorageFilesystem.checked_existence:
            StorageFilesystem.checked_existence = True
            if not os.path.exists(StorageFilesystem.basepath):
                os.makedirs(StorageFilesystem.basepath)

        filename = StorageFilesystem.filename_for_key(key)

        sio = StringIO()
        try:
            pickle.dump(value, sio, pickle.HIGHEST_PROTOCOL)
        except Exception as e:
            msg = ('Cannot set key %s: cannot pickle object '
                    'of class %s: %s' % (key, value.__class__.__name__, e))
            msg += '\n%s' % find_pickling_error(value)
            raise SerializationError(msg)

        with safe_write(filename, 'wb') as f:
            f.write(sio.getvalue())

    @staticmethod
    @track_time
    def delete(key):
        filename = StorageFilesystem.filename_for_key(key)
        assert os.path.exists(filename), \
            'I expected path %s to exist before deleting' % filename
        os.remove(filename)

    @staticmethod
    @track_time
    def exists(key):
        filename = StorageFilesystem.filename_for_key(key)
        return os.path.exists(filename)

    @staticmethod
    # TODO change key
    def keys_yield(pattern):
        filename = StorageFilesystem.filename_for_key(pattern)
        for x in glob(filename):
            b = splitext(basename(x))[0]
            yield StorageFilesystem.filename2key(b)

    @staticmethod
    @track_time
    def keys(pattern):
        return sorted(list(StorageFilesystem.keys_yield(pattern)))

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




