from compmake.structures import CompmakeException, SerializationError
from compmake.utils import find_pickling_error, safe_pickle_load, safe_pickle_dump
from compmake import logger
from glob import glob
from os.path import basename
import cPickle as pickle
import os
import traceback
import fnmatch
from contracts import contract

if False:
    track_time = lambda x: x
else:
    from ..utils import TimeTrack
    track_time = TimeTrack.decorator

trace_queries = False

__all__ = ['StorageFilesystem2']

class StorageFilesystem2(object):

    def __init__(self, basepath, compress=False):
        self.basepath = basepath
        self.checked_existence = False
        if compress:
            self.file_extension = '.pickle.gz'
        else:
            self.file_extension = '.pickle'

    def __repr__(self):
        return "FilesystemDB2(%r)" % self.basepath

    @track_time
    def __getitem__(self, key):
        if trace_queries:
            logger.debug('R %s' % str(key))
        
        self.check_existence()
        
        filename = self.filename_for_key(key)
        
        if not os.path.exists(filename):
            raise CompmakeException('Could not find key %r.' % key)
        
        try:
            return safe_pickle_load(filename)
        except Exception as e:
            msg = "Could not unpickle file %r." % (filename)
            logger.error(msg)
            logger.exception(e)
            msg += "\n" + traceback.format_exc(e)
            raise CompmakeException(msg)

    def check_existence(self):
        if not self.checked_existence:
            self.checked_existence = True
            if not os.path.exists(self.basepath):
                logger.info('Creating basepath %r' % self.basepath)
                os.makedirs(self.basepath)

    @track_time
    def __setitem__(self, key, value):  # @ReservedAssignment
        if trace_queries:
            logger.debug('W %s' % str(key))

        self.check_existence()

        filename = self.filename_for_key(key)
        dirname = os.path.dirname(filename)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
            
        protocol = pickle.HIGHEST_PROTOCOL
        try:
            paranoid = False
            if paranoid:        
                safe_pickle_dump(value, filename, protocol)
            else:
                with open(filename, 'wb') as f:
                    pickle.dump(value, f, protocol)

        except Exception as e:
            msg = ('Cannot set key %s: cannot pickle object '
                    'of class %s: %s' % (key, value.__class__.__name__, e))
            logger.error(msg)
            logger.exception(e)
            emsg = find_pickling_error(value)
            logger.error(emsg)
            raise SerializationError(msg + '\n' + emsg)

    @track_time
    def __delitem__(self, key):
        filename = self.filename_for_key(key)
        if not os.path.exists(filename):
            msg = 'I expected path %s to exist before deleting' % filename
            raise ValueError(msg)
        os.remove(filename)

    @track_time
    def __contains__(self, key):
        if trace_queries:
            logger.debug('? %s' % str(key))

        filename = self.filename_for_key(key)
        return os.path.exists(filename)
  
    @track_time
    def keys0(self):        
        for _, _, files in os.walk(self.basepath, followlinks=False):
            for f in files:
                if self.file_extension in f:
                    b = basename(f.replace(self.file_extension, ''))
                    key = self.basename2key(b)
                    yield key
                      
    @track_time
    def keys(self):
        # slow process
        found = sorted(list(self.keys0()))
        return found

    def reopen_after_fork(self):
        pass

    dangerous_chars = {
       '/': 'CMSLASH',
       '..': 'CMDOT',
       '~': 'CMHOME'
    }

    def key2basename(self, key):
        '''turns a key into a reasonable filename'''
        for char, replacement in self.dangerous_chars.items():
            key = key.replace(char, replacement)
        return key

    def basename2key(self, key):
        ''' Undoes key2basename '''
        for char, replacement in StorageFilesystem2.dangerous_chars.items():
            key = key.replace(replacement, char)
        return key

    def filename_for_key(self, key):
        """ Returns the pickle storage filename corresponding to the job id """
        basename = self.key2basename(key)
        components = "/".join(basename.split(':'))
        f = components + '/' + basename + self.file_extension
        return os.path.join(self.basepath, f)


# @contract(returns='list(str)', directory='str',
#           pattern='str', followlinks='bool')
# def locate_files(directory, pattern, followlinks=True):
#     filenames = []
#     
#     for root, _, files in os.walk(directory, followlinks=followlinks):
#         for f in files:
#             if fnmatch.fnmatch(f, pattern):
#                 filename = os.path.join(root, f)
#                 filenames.append(filename)
# 
#     real2norm = defaultdict(lambda: [])
#     for norm in filenames:
#         real = os.path.realpath(norm)
#         real2norm[real].append(norm)
#         # print('%s -> %s' % (real, norm))
# 
#     for k, v in real2norm.items():
#         if len(v) > 1:
#             msg = 'In directory:\n\t%s\n' % directory
#             msg += 'I found %d paths that refer to the same file:\n'
#             for n in v:
#                 msg += '\t%s\n' % n
#             msg += 'refer to the same file:\n\t%s\n' % k
#             msg += 'I will silently eliminate redundancies.'
#             logger.warning(v)
# 
#     return real2norm.keys()






