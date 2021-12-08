from typing import cast

from zuper_commons.test_utils import my_assert_equal as assert_equal


from compmake import StorageKey
from compmake.utils import wildcard_to_regexp
from .utils import Env, run_with_env


@run_with_env
async def test_exists1(env: Env):
    key = cast(StorageKey, "not-existent")
    assert not key in env.db


@run_with_env
async def test_exists2(env: Env):
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
async def test_search(env: Env):
    db = env.db

    def search(pattern):
        r = wildcard_to_regexp(pattern)
        for k in db.keys():
            if r.match(k):
                yield k

    assert_equal([], list(search("*")))
    k1 = cast(StorageKey, "key1")
    k2 = cast(StorageKey, "key2")
    db[k1] = 1
    db[k2] = 1
    assert_equal([], list(search("ciao*")))
    assert_equal(["key1"], list(search("key1")))
    assert_equal(["key1"], list(search("*1")))
    assert_equal([], list(search("d*1")))
