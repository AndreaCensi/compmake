from contextlib import asynccontextmanager
from typing import cast, List

from compmake import (
    MakeFailed,
)
from compmake_tests.utils import Env


@asynccontextmanager
async def assert_MakeFailed(env: Env, nfailed: int, nblocked: int):
    try:
        yield
    except MakeFailed as e:
        found_failed = cast(List[str], e.info["failed"])
        found_blocked = cast(List[str], e.info["blocked"])
        if len(found_failed) != nfailed:
            msg = f"Expected {nfailed} failed, got {len(found_failed)}: {found_failed}"
            raise Exception(msg)
        if len(found_blocked) != nblocked:
            msg = f"Expected {nblocked} blocked, got {len(found_blocked)}: {found_blocked}"
            raise Exception(msg)
    except Exception as e:
        raise Exception("unexpected: %s" % e)
