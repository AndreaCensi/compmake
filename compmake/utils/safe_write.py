from contextlib import contextmanager
import os


@contextmanager
def safe_write(filename, mode='wb'):
    tmp_filename = '%s.tmp' % filename
    try:
        with open(tmp_filename, mode) as f:
            yield f
        if os.path.exists(filename):
            os.unlink(filename)
        os.rename(tmp_filename, filename)
    except:
        if os.path.exists(tmp_filename):
            os.unlink(tmp_filename)
        raise
