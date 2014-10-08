import os

__all__ = [
    'which',
]


def is_exe(fpath):
    return os.path.exists(fpath) and os.access(fpath, os.X_OK)


def ext_candidates(fpath):
    yield fpath
    for ext in os.environ.get("PATHEXT", "").split(os.pathsep):
        yield fpath + ext


def which(program):
    """ Returns string or raise ValueError. """
    PATH = os.environ["PATH"]
    PATHs = PATH.split(os.pathsep)

    fpath, _ = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in PATHs:
            exe_file = os.path.join(path, program)
            for candidate in ext_candidates(exe_file):
                if is_exe(candidate):
                    return candidate

    msg = 'Could not find program %r.' % program
    msg += '\n paths = %s' % PATH
    raise ValueError(msg)
