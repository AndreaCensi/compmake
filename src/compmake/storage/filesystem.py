import os
import stat
import traceback
from glob import glob
from os.path import basename
from typing import Iterator, List, NewType

import dill

from compmake import logger
from compmake.exceptions import CompmakeBug, SerializationError
from compmake.utils import safe_pickle_dump, safe_pickle_load
from zuper_commons.fs import (
    DirPath,
    FilePath,
    find_pickling_error,
    safe_read,
    safe_write,
    write_ustring_to_utf8_file,
)
from zuper_commons.types import ZException

__all__ = [
    "StorageFilesystem",
    "StorageKey",
]
if True:

    def track_time(x):
        return x


else:
    from ..utils import TimeTrack

    track_time = TimeTrack.decorator

trace_queries = False

StorageKey = NewType("StorageKey", str)


class StorageFilesystem:
    basepath: DirPath
    checked_existence: bool
    method: str
    """ `pickle` or `dill` """
    file_extension: str

    def __init__(self, basepath: DirPath, compress: bool = False):
        self.basepath = os.path.realpath(basepath)
        self.checked_existence = False
        self.method = method = "pickle"

        if compress:
            self.file_extension = f".{method}.gz"
            others = list(self.keys0(f".{method}"))
        else:
            self.file_extension = f".{method}"
            others = list(self.keys0(f".{method}.gz"))
        if others:
            msg = "Extension is %s but found %s files with other extension." % (
                self.file_extension,
                len(others),
            )
            raise ZException(msg)

        # create a bunch of files that contain shortcuts
        create_scripts(self.basepath)

    def __repr__(self) -> str:
        return f"FilesystemDB({self.basepath!r};{self.file_extension})"

    @track_time
    def sizeof(self, key: StorageKey) -> int:
        filename = self.filename_for_key(key)
        statinfo = os.stat(filename)
        return statinfo.st_size

    @track_time
    def __getitem__(self, key: StorageKey) -> object:
        if trace_queries:
            logger.debug("R %s" % str(key))

        self.check_existence()

        filename = self.filename_for_key(key)

        if not os.path.exists(filename):
            msg = f"Could not find key {key!r}."
            msg += f"\n file: {filename}"
            raise CompmakeBug(msg)

        if self.method == "pickle":
            try:
                return safe_pickle_load(filename)
            except Exception as e:
                msg = f"Could not unpickle data for key {key!r}. \n file: {filename}"
                logger.error(msg)
                logger.exception(e)
                msg += "\n" + traceback.format_exc()
                raise CompmakeBug(msg)
        elif self.method == "dill":
            with safe_read(filename) as f:
                return dill.load(f)
        else:
            raise NotImplementedError(self.method)

    def check_existence(self) -> None:
        if not self.checked_existence:
            self.checked_existence = True
            if not os.path.exists(self.basepath):
                # logger.info('Creating filesystem db %r' % self.basepath)
                os.makedirs(self.basepath)

    @track_time
    def __setitem__(self, key: StorageKey, value: object) -> None:  # @ReservedAssignment
        if trace_queries:
            logger.debug(f"W {str(key)}")

        self.check_existence()

        filename = self.filename_for_key(key)

        if self.method == "pickle":
            try:
                safe_pickle_dump(value, filename)
                assert os.path.exists(filename)
            except KeyboardInterrupt:
                raise
            except BaseException as e:
                msg = f"Cannot set key {key}: cannot pickle object of class {value.__class__.__name__}"
                logger.error(msg, e=traceback.format_exc())
                # logger.exception(e)
                emsg = find_pickling_error(value)
                logger.error(emsg)
                raise SerializationError(msg + "\n" + emsg)
        elif self.method == "dill":
            dill.settings["recurse"] = True
            dill.settings["byref"] = True
            with safe_write(filename) as f:
                return dill.dump(value, f)
        else:
            raise NotImplementedError(self.method)

    @track_time
    def __delitem__(self, key: StorageKey) -> None:
        filename = self.filename_for_key(key)
        if not os.path.exists(filename):
            msg = "I expected path %s to exist before deleting" % filename
            raise ValueError(msg)
        os.remove(filename)

    @track_time
    def __contains__(self, key: StorageKey) -> bool:
        if trace_queries:
            logger.debug(f"? {str(key)}")

        filename = self.filename_for_key(key)
        ex = os.path.exists(filename)

        # logger.debug('? %s %s %s' % (str(key), filename, ex))
        return ex

    @track_time
    def keys0(self, extension: str = None) -> Iterator[StorageKey]:
        if extension is None:
            extension = self.file_extension
        filename = self.filename_for_key("*", extension)
        for x in glob(filename):
            # b = splitext(basename(x))[0]
            b = basename(x.replace(extension, ""))
            key = self.basename2key(b)
            yield key

    @track_time
    def keys(self) -> List[StorageKey]:
        # slow process
        found = sorted(list(self.keys0()))
        return found

    def reopen_after_fork(self) -> None:
        pass

    dangerous_chars = {"/": "CMSLASH", "..": "CMDOT", "~": "CMHOME"}

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

    def filename_for_key(self, key, extension=None) -> FilePath:
        """ Returns the pickle storage filename corresponding to the job id """
        if extension is None:
            extension = self.file_extension
        f = self.key2basename(key) + extension
        return os.path.join(self.basepath, f)


def chmod_plus_x(filename: FilePath) -> None:
    st = os.stat(filename)
    os.chmod(filename, st.st_mode | stat.S_IEXEC)


def create_scripts(basepath: DirPath) -> None:
    filename2cmd = {
        "ls_failed": "ls failed",
        "why_failed": "why failed",
        "make_failed": "make failed",
        "remake": "remake",
        "why": "why",
        "make": "make",
        "parmake": "parmake",
        "rparmake": "rparmake",
        "rmake": "rmake",
        "clean": "clean",
        "ls": "ls",
        "stats": "stats",
        "gantt": "gantt",
        "details": "details",
    }
    for fn, cmd in filename2cmd.items():
        s = f'#!/bin/bash\ncompmake {basepath} -c "{cmd} $*"\n'
        f = os.path.join(basepath, fn)
        write_ustring_to_utf8_file(s, f, quiet=True)
        chmod_plus_x(f)

    s = f"#!/bin/bash\ncompmake {basepath} \n"
    f = os.path.join(basepath, "console")
    write_ustring_to_utf8_file(s, f, quiet=True)
    chmod_plus_x(f)

    s = f'#!/bin/bash\ncompmake {basepath} -c "$*" \n'
    f = os.path.join(basepath, "run")
    write_ustring_to_utf8_file(s, f, quiet=True)
    chmod_plus_x(f)
