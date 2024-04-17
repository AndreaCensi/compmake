import os
import pickle
import sqlite3
import stat
import traceback
from asyncio import CancelledError
from typing import Iterator, NewType, Optional, TypeVar

import dill

from zuper_commons.fs import (
    DirPath,
    FilePath,
    join,
    write_ustring_to_utf8_file,
)
from zuper_commons.types import contextmanager
from zuper_utils_timing.timing import new_timeinfo
from . import logger
from .exceptions import SerializationError

__all__ = [
    "StorageFilesystem",
    "StorageKey",
]

X = TypeVar("X")


def track_time(x: X) -> X:
    return x


trace_queries = False

StorageKey = NewType("StorageKey", str)


class StorageFilesystem:
    basepath: DirPath
    method: str
    """ `pickle` or `dill` """
    file_extension: str

    def __init__(self, basepath: DirPath, compress: bool = True):
        if not compress:
            raise Exception()
        self.basepath = os.path.realpath(basepath)
        if not os.path.exists(self.basepath):
            os.makedirs(self.basepath, exist_ok=True)
        self.fn = os.path.join(self.basepath, "db.sqlite")
        existed = os.path.exists(self.fn)
        if not existed:
            logger.info(f"The database {self.fn!r} did not exist: creating.")
        self.con = sqlite3.connect(self.fn, timeout=15)
        if not existed:
            with self.cursor() as cur:
                sql = """
                create table fs_blobs(blob_key text not null primary key , blob_value blob)
                """
                cur.execute(sql)
                # sql = """
                # create index blob_keys on fs_blobs(blob_key);
                # """
                # cur.execute(sql)
                self.con.commit()

        self.method = method = "pickle"
        # self.method = method= "dill"
        # check_format = False  # XXX: quadratic complexity!
        # others = []
        # if compress:
        #     self.file_extension = f".{method}.gz"
        #     if check_format:
        #         others = list(self.keys0(f".{method}"))
        # else:
        #     self.file_extension = f".{method}"
        #     if check_format:
        #         others = list(self.keys0(f".{method}.gz"))
        # if others:
        #     msg = f"Extension is {self.file_extension} but found {len(others)} files with other extension."
        #     msg += f" Check that you did not use compress = {not compress} somewhere else."
        #     raise ZException(msg, others=others)

        # create a bunch of files that contain shortcuts
        create_scripts(self.basepath)

    @contextmanager
    def cursor(self) -> Iterator[sqlite3.Cursor]:
        cur = self.con.cursor()
        try:
            yield cur
        finally:
            cur.close()

    def close(self) -> None:
        self.con.close()

    def __repr__(self) -> str:
        return f"FilesystemDB({self.basepath!r};{self.file_extension})"

    @track_time
    def sizeof(self, key: StorageKey) -> int:
        with self.cursor() as cur:
            # filename = self.filename_for_key(key)
            sql = """
                select length(blob_value) from fs_blobs where blob_key = ?
            """
            cur.execute(sql, (key,))
            (res,) = cur.fetchone()
            return res
        # statinfo = os.stat(filename)
        # return statinfo.st_size

    @track_time
    def __getitem__(self, key: StorageKey) -> object:
        if trace_queries:
            logger.debug("R %s" % str(key))

        # self.check_existence()

        with self.cursor() as cur:
            sql = """
                select blob_value from fs_blobs where blob_key = ?
            """
            cur.execute(sql, (key,))
            one = cur.fetchone()
            if one is None:
                raise KeyError(key)
            (data,) = one

        # filename = self.filename_for_key(key)
        #
        # if not os.path.exists(filename):
        #     msg = f"Could not find key {key!r}."
        #     msg += f"\n file: {filename}"
        #     raise CompmakeBug(msg)

        if self.method == "pickle":
            return pickle.loads(data)
            # try:
            #     return safe_pickle_load(filename)
            # except Exception as e:
            #     msg = f"Could not unpickle data for key {key!r}. \n file: {filename}"
            #     logger.error(msg)
            #     # logger.exception(e)
            #     msg += "\n" + traceback.format_exc()
            #     raise CompmakeBug(msg)
        elif self.method == "dill":
            return dill.loads(data)
            # with safe_read(filename, "rb") as f:
            #     return dill.load(f)
        else:
            raise NotImplementedError(self.method)

    # def check_existence(self) -> None:
    #     if not self.checked_existence:
    #         self.checked_existence = True
    #         if not os.path.exists(self.basepath):
    #             # logger.info('Creating filesystem db %r' % self.basepath)
    #             os.makedirs(self.basepath, exist_ok=True)

    @track_time
    def __setitem__(self, key: StorageKey, value: object) -> None:  # @ReservedAssignment
        if trace_queries:
            logger.debug(f"W {str(key)}")
        # DOSYNC = False
        ti = new_timeinfo()
        try:
            # self.check_existence()

            # filename = self.filename_for_key(key)

            if self.method == "pickle":
                try:
                    with ti.timeit("safe_pickle_dump"):
                        data = pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
                    #     safe_pickle_dump(value, filename)
                    # if DOSYNC:
                    #     with ti.timeit("os.sync"):
                    #         os.sync()  # flush everything

                    # assert os.path.exists(filename)
                except KeyboardInterrupt:
                    raise
                except CancelledError:
                    raise
                except BaseException as e:
                    msg = f"Cannot set key {key!r}: cannot pickle object of class {value.__class__.__name__}"
                    # raise SerializationError(msg, tb=traceback.format_exc(), ob=value) from e
                    # logger.error(msg, e=traceback.format_exc())
                    # logger.exception(e)
                    # emsg = find_pickling_error(value)
                    # logger.error(emsg)
                    raise SerializationError(msg, tb=traceback.format_exc(), value=value) from e
            elif self.method == "dill":
                dill.settings["recurse"] = True
                dill.settings["byref"] = True
                data = dill.dumps(value)
                # with safe_write(filename, "wb") as f:
                #     return dill.dump(value, f)
            else:
                raise NotImplementedError(self.method)
        finally:
            pass
            # print(ti.pretty())

        sql = """
        insert into fs_blobs(blob_key, blob_value) values (?, ?)
        on conflict(blob_key) do update set blob_value = excluded.blob_value
        """
        with self.cursor() as cur:
            cur.execute(sql, (key, data))
            self.con.commit()

    @track_time
    def __delitem__(self, key: StorageKey) -> None:
        sql = """
        delete from fs_blobs where blob_key = ?
        """
        with self.cursor() as cur:
            cur.execute(sql, (key,))
            self.con.commit()

        # filename = self.filename_for_key(key)
        # if not os.path.exists(filename):
        #     msg = "I expected path %s to exist before deleting" % filename
        #     raise ValueError(msg)
        # os.remove(filename)

    @track_time
    def __contains__(self, key: StorageKey) -> bool:
        if trace_queries:
            logger.debug(f"? {str(key)}")
        #
        # filename = self.filename_for_key(key)
        # ex = os.path.exists(filename)

        sql = """
            select count(*) from fs_blobs where blob_key = ?
        """
        with self.cursor() as cur:
            cur.execute(sql, (key,))
            (res,) = cur.fetchone()
            return res > 0
        # logger.debug('? %s %s %s' % (str(key), filename, ex))
        # return ex

    @track_time
    def keys0(self, extension: Optional[str] = None) -> Iterator[StorageKey]:
        sql = """
            select blob_key from fs_blobs
        """
        with self.cursor() as cur:
            cur.execute(sql)
            res = cur.fetchall()
            for row in res:
                yield row[0]
        # if extension is None:
        #     extension = self.file_extension
        # filename = self.filename_for_key("*", extension)
        # for x in glob(filename):
        #     # b = splitext(basename(x))[0]
        #     b = basename(x.replace(extension, ""))
        #     key = self.basename2key(b)
        #     yield key

    @track_time
    def keys(self) -> list[StorageKey]:
        # slow process
        found = sorted(list(self.keys0()))
        return found

    #
    # def reopen_after_fork(self) -> None:
    #     self.con = sqlite3.connect(self.fn)

    dangerous_chars = {"/": "CMSLASH", "..": "CMDOT", "~": "CMHOME"}

    def key2basename(self, key: str) -> str:
        """turns a key into a reasonable filename"""
        for char, replacement in self.dangerous_chars.items():
            key = key.replace(char, replacement)
        return key

    def basename2key(self, key: str) -> str:
        """Undoes key2basename"""
        for char, replacement in StorageFilesystem.dangerous_chars.items():
            key = key.replace(replacement, char)
        return key

    # def filename_for_key(self, key, extension=None) -> FilePath:
    #     """Returns the pickle storage filename corresponding to the job id"""
    #     if extension is None:
    #         extension = self.file_extension
    #     f = self.key2basename(key) + extension
    #     return join(self.basepath, f)


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
        "cmake": "make",
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
        f = join(basepath, fn)
        write_ustring_to_utf8_file(s, f, quiet=True)
        chmod_plus_x(f)

    s = f"#!/bin/bash\ncompmake {basepath} \n"
    f = join(basepath, "console")
    write_ustring_to_utf8_file(s, f, quiet=True)
    chmod_plus_x(f)
    # s = f"#!/bin/bash\ncompmake {basepath} \n"
    # f = join(basepath, "compmake")
    # write_ustring_to_utf8_file(s, f, quiet=True)
    # chmod_plus_x(f)

    s = f'#!/bin/bash\ncompmake {basepath} -c "$*" \n'
    f = join(basepath, "cm")
    write_ustring_to_utf8_file(s, f, quiet=True)
    chmod_plus_x(f)

    s = f"#!/bin/bash\ncompmake-profile {basepath} $* \n"
    f = join(basepath, "profile")
    write_ustring_to_utf8_file(s, f, quiet=True)
    chmod_plus_x(f)
