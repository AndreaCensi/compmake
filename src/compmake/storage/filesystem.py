# -*- coding: utf-8 -*-
import os
import stat
import traceback
from glob import glob
from os.path import basename

from compmake import logger
from compmake.exceptions import CompmakeBug, SerializationError
from compmake.utils import (find_pickling_error, safe_pickle_dump,
                            safe_pickle_load)
from compmake.utils.safe_write import write_data_to_file

if True:
    track_time = lambda x: x
else:
    from ..utils import TimeTrack

    track_time = TimeTrack.decorator

trace_queries = False

__all__ = [
    'StorageFilesystem',
]


class StorageFilesystem(object):

    def __init__(self, basepath, compress=False):
        self.basepath = os.path.realpath(basepath)
        self.checked_existence = False
        if compress:
            self.file_extension = '.pickle.gz'
        else:
            self.file_extension = '.pickle'

        # create a bunch of files that contain shortcuts
        create_scripts(self.basepath)

    def __repr__(self):
        return "FilesystemDB(%r)" % self.basepath

    @track_time
    def sizeof(self, key):
        filename = self.filename_for_key(key)
        statinfo = os.stat(filename)
        return statinfo.st_size

    @track_time
    def __getitem__(self, key):
        if trace_queries:
            logger.debug('R %s' % str(key))

        self.check_existence()

        filename = self.filename_for_key(key)

        if not os.path.exists(filename):
            msg = 'Could not find key %r.' % key
            msg += '\n file: %s' % filename
            raise CompmakeBug(msg)

        try:
            return safe_pickle_load(filename)
        except Exception as e:
            msg = ("Could not unpickle data for key %r. \n file: %s" %
                   (key, filename))
            logger.error(msg)
            logger.exception(e)
            msg += "\n" + traceback.format_exc()
            raise CompmakeBug(msg)

    def check_existence(self):
        if not self.checked_existence:
            self.checked_existence = True
            if not os.path.exists(self.basepath):
                # logger.info('Creating filesystem db %r' % self.basepath)
                os.makedirs(self.basepath)

    @track_time
    def __setitem__(self, key, value):  # @ReservedAssignment
        if trace_queries:
            logger.debug('W %s' % str(key))

        self.check_existence()

        filename = self.filename_for_key(key)

        try:
            safe_pickle_dump(value, filename)
            assert os.path.exists(filename)
        except KeyboardInterrupt:
            raise
        except BaseException as e:
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
        ex = os.path.exists(filename)

        # logger.debug('? %s %s %s' % (str(key), filename, ex))
        return ex

    @track_time
    def keys0(self):
        filename = self.filename_for_key('*')
        for x in glob(filename):
            # b = splitext(basename(x))[0]
            b = basename(x.replace(self.file_extension, ''))
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
        """ turns a key into a reasonable filename"""
        for char, replacement in self.dangerous_chars.items():
            key = key.replace(char, replacement)
        return key

    def basename2key(self, key):
        """ Undoes key2basename """
        for char, replacement in StorageFilesystem.dangerous_chars.items():
            key = key.replace(replacement, char)
        return key

    def filename_for_key(self, key):
        """ Returns the pickle storage filename corresponding to the job id """
        f = self.key2basename(key) + self.file_extension
        return os.path.join(self.basepath, f)


def chmod_plus_x(filename):
    st = os.stat(filename)
    os.chmod(filename, st.st_mode | stat.S_IEXEC)


def create_scripts(basepath):
    filename2cmd = \
        {'ls_failed': 'ls failed',
         'why_failed': 'why failed',
         'make_failed': 'make failed',
         'remake': 'remake',
         'make': 'make',
         'parmake': 'parmake',
         'rparmake': 'rparmake',
         'rmake': 'rmake',
         'ls': 'ls',
         'stats': 'stats',
         'details': 'details',
         }
    for fn, cmd in filename2cmd.items():
        s = "#!/bin/bash\ncompmake %s -c \"%s $*\"\n" % (basepath, cmd)
        f = os.path.join(basepath, fn)
        write_data_to_file(s, f, quiet=True)
        chmod_plus_x(f)

    s = "#!/bin/bash\ncompmake %s \n" % (basepath)
    f = os.path.join(basepath, 'console')
    write_data_to_file(s, f, quiet=True)
    chmod_plus_x(f)

    s = "#!/bin/bash\ncompmake %s -c \"$*\" \n" % (basepath)
    f = os.path.join(basepath, 'run')
    write_data_to_file(s, f, quiet=True)
    chmod_plus_x(f)
