import sys

from zuper_commons.fs import read_ustring_from_utf8_file


def make_bridge_main(args=None):
    fn = sys.argv[1]

    fn = read_ustring_from_utf8_file(fn)


    lines = fn.split()

    for line in lines:
        line = remove_comments(line)


def remove_comments(line: str) -> str:
    pass
