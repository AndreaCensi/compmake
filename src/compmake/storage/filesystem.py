from .. import logger
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

    def __init__(self, basepath):
        self.basepath = basepath
        self.checked_existence = False

    def __str__(self):
        return "Filesystem backend"

    def supports_concurrency(self):
        return False

    @track_time
    def get(self, key):
        self.check_existence()

        if not self.exists(key):
            raise CompmakeException('Could not find key %r.' % key)
        filename = self.filename_for_key(key)
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

    def check_existence(self):
        if not self.checked_existence:
            self.checked_existence = True
            if not os.path.exists(self.basepath):
                logger.info('Creating basepath %r' % self.basepath)
                os.makedirs(self.basepath)

    @track_time
    def set(self, key, value):  # @ReservedAssignment
        self.check_existence()

        filename = self.filename_for_key(key)

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

    @track_time
    def delete(self, key):
        filename = self.filename_for_key(key)
        assert os.path.exists(filename), \
            'I expected path %s to exist before deleting' % filename
        os.remove(filename)

    @track_time
    def exists(self, key):
        filename = self.filename_for_key(key)
        return os.path.exists(filename)

    # TODO change key
    def keys_yield(self, pattern):
        filename = self.filename_for_key(pattern)
        for x in glob(filename):
            b = splitext(basename(x))[0]
            yield self.filename2key(b)

    @track_time
    def keys(self, pattern):
        return sorted(list(self.keys_yield(pattern)))

    def reopen_after_fork(self):
        pass

    dangerous_chars = {
       '/': 'CMSLASH',
       '..': 'CMDOT',
       '~': 'CMHOME'
    }

    def key2filename(self, key):
        '''turns a key into a reasonable filename'''
        for char, replacement in self.dangerous_chars.items():
            key = key.replace(char, replacement)
        return key

    def filename2key(self, key):
        ''' Undoes key2filename '''
        for char, replacement in StorageFilesystem.dangerous_chars.items():
            key = key.replace(replacement, char)
        return key

    def filename_for_key(self, key):
        """ Returns the pickle storage filename corresponding to the job id """
        return os.path.join(self.basepath, self.key2filename(key) + '.pickle')




