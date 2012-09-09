from contextlib import contextmanager
import os
import gzip

def is_gzip_filename(filename):
    return '.gz' in filename 

@contextmanager
def safe_write(filename, mode='wb', compresslevel=5):
    """ 
        Makes atomic writes by writing to a temp filename. 
        Also if the filename ends in ".gz", writes to a compressed stream.
        Yields a file descriptor.
    """
    tmp_filename = '%s.tmp' % filename
    try:
        if is_gzip_filename(filename):
            fopen = lambda f, mode: gzip.open(filename=f, mode=mode,
                                              compresslevel=compresslevel)
        else:
            fopen = open
                     
        with fopen(tmp_filename, mode) as f:
            yield f
            
        if os.path.exists(filename):
            os.unlink(filename)
        os.rename(tmp_filename, filename)
    except:
        if os.path.exists(tmp_filename):
            os.unlink(tmp_filename)
        raise


@contextmanager
def safe_read(filename, mode='rb'):
    """ 
        If the filename ends in ".gz", reads from a compressed stream.
        Yields a file descriptor.
    """
    try:
        if is_gzip_filename(filename):
            fopen = gzip.open
        else:
            fopen = open
        
        with fopen(filename, mode) as f:
            yield f
    except:
        # TODO
        raise
