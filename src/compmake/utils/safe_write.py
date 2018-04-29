# -*- coding: utf-8 -*-
from contextlib import contextmanager
import gzip
import os
from compmake.utils.filesystem_utils import make_sure_dir_exists
from compmake.utils.friendly_path_imp import friendly_path
from compmake import logger

__all__ = [
    'safe_write',
    'safe_read',
]


def is_gzip_filename(filename):
    return '.gz' in filename


@contextmanager
def safe_write(filename, mode='wb', compresslevel=5):
    """ 
        Makes atomic writes by writing to a temp filename. 
        Also if the filename ends in ".gz", writes to a compressed stream.
        Yields a file descriptor.
        
        It is thread safe because it renames the file.
        If there is an error, the file will be removed if it exists.
    """
    dirname = os.path.dirname(filename)
    if dirname:
        if not os.path.exists(dirname):
            try:
                os.makedirs(dirname)
            except:
                pass

                # Dont do this!
                # if os.path.exists(filename):
                # os.unlink(filename)
                #     assert not os.path.exists(filename)
                #
    tmp_filename = '%s.tmp.%s' % (filename, os.getpid())
    try:
        if is_gzip_filename(filename):
            fopen = lambda fname, fmode: gzip.open(filename=fname, mode=fmode,
                                                   compresslevel=compresslevel)
        else:
            fopen = open

        with fopen(tmp_filename, mode) as f:
            yield f
        f.close()

        # if os.path.exists(filename):
        # msg = 'Race condition for writing to %r.' % filename
        #             raise Exception(msg)
        #
        # On Unix, if dst exists and is a file, it will be replaced silently
        #  if the user has permission.
        os.rename(tmp_filename, filename)
    except:
        if os.path.exists(tmp_filename):
            os.unlink(tmp_filename)
        if os.path.exists(filename):
            os.unlink(filename)
        raise


@contextmanager
def safe_read(filename, mode='rb'):
    """ 
        If the filename ends in ".gz", reads from a compressed stream.
        Yields a file descriptor.
    """
    try:
        if is_gzip_filename(filename):
            f = gzip.open(filename, mode)
            try:
                yield f
            finally:
                f.close()

        else:
            with open(filename, mode) as f:
                yield f
    except:
        # TODO
        raise


def write_data_to_file(data, filename, quiet=False):
    """ 
        Writes the data to the given filename. 
        If the data did not change, the file is not touched.
    
    """
    if not isinstance(data, str):
        msg = 'Expected "data" to be a string, not %s.' % type(data).__name__
        raise ValueError(msg)
    if len(filename) > 256:
        msg = 'Invalid argument filename: too long. Did you confuse it with data?'
        raise ValueError(msg)
    
    
    make_sure_dir_exists(filename)
    
    if os.path.exists(filename):
        current = open(filename).read()
        if current == data:
            if not 'assets' in filename:
                if not quiet:
                    logger.debug('already up to date %s' % friendly_path(filename))
            return
         
    with open(filename, 'w') as f:
        f.write(data)
        
    if not quiet:
        logger.debug('Written to: %s' % friendly_path(filename))
