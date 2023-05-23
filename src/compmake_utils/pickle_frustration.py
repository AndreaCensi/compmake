import os
import sys
from contextlib import contextmanager
from typing import cast, Iterator, TypedDict


class PickleContextDesc(TypedDict):
    main_module: str
    main_path: str


def pickle_main_context_save() -> PickleContextDesc:
    """Remember who was the __main__ module"""
    module = sys.modules["__main__"]
    filename = cast(str, module.__file__)
    name = os.path.splitext(os.path.basename(filename))[0]
    main_module = name
    main_path = os.path.realpath(os.path.dirname(filename))
    return dict(main_module=main_module, main_path=main_path)


@contextmanager
def pickle_main_context_load(c: PickleContextDesc) -> Iterator[None]:
    main_path = c["main_path"]
    main_module = c["main_module"]

    try:
        if not main_path in sys.path:
            sys.path.append(main_path)

        cur_main = sys.modules["__main__"]

        try:
            m = __import__(main_module, fromlist=["dummy"])
            m.__name__ = "__main__"
            sys.modules["__main__"] = m
        except ImportError as e:
            #             print('pickle_main_context_load: Cannot import %r: %s'
            #                   % (main_module, e))
            pass
        yield

    finally:
        # noinspection PyUnboundLocalVariable
        sys.modules["__main__"] = cur_main
