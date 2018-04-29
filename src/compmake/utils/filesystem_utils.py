# -*- coding: utf-8 -*-
import os

__all__ = [
    'make_sure_dir_exists',
    'mkdirs_thread_safe',
]


def mkdirs_thread_safe(dst):
    """ Make directories leading to 'dst' if they don't exist yet"""
    if dst == '' or os.path.exists(dst):
        return
    head, _ = os.path.split(dst)
    if os.sep == ':' and not ':' in head:
        head += ':'
    mkdirs_thread_safe(head)
    try:
        mode = 511  # 0777 in octal
        os.mkdir(dst, mode)
    except OSError as err:
        if err.errno != 17:  # file exists
            raise


def make_sure_dir_exists(filename):
    """ Makes sure that the path to file exists, but creating directories. """
    dirname = os.path.dirname(filename)
    # dir == '' for current dir
    if dirname != '' and not os.path.exists(dirname):
        mkdirs_thread_safe(dirname)
