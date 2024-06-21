from typing import Iterator, cast

from compmake import StorageKey
from zuper_commons.test_utils import my_assert, my_assert_equal
from zuper_commons.text import wildcard_to_regexp
from .utils import Env, run_with_env


@run_with_env
async def test_exists1(env: Env) -> None:
    key = cast(StorageKey, "not-existent")
    my_assert(key not in env.db)


@run_with_env
async def test_exists2(env: Env) -> None:
    k = cast(StorageKey, "ciao")
    v = {"complex": 123}
    db = env.db
    # if k in db:
    #     del db[k]
    assert not (k in db)
    db[k] = v
    assert k in db
    del db[k]
    assert not (k in db)
    db[k] = v
    del db[k]
    assert not (k in db)


@run_with_env
async def test_search(env: Env) -> None:
    db = env.db

    def search(pattern: str) -> Iterator[str]:
        r = wildcard_to_regexp(pattern)
        for k in db.keys0():
            if r.match(k):
                yield k

    my_assert_equal([], list(search("*")))
    k1 = cast(StorageKey, "key1")
    k2 = cast(StorageKey, "key2")
    db[k1] = 1
    db[k2] = 1
    my_assert_equal([], list(search("ciao*")))
    my_assert_equal(["key1"], list(search("key1")))
    my_assert_equal(["key1"], list(search("*1")))
    my_assert_equal([], list(search("d*1")))
