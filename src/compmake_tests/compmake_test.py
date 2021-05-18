from contextlib import asynccontextmanager

from compmake import (
    MakeFailed,
)
from compmake_tests.utils import Env


@asynccontextmanager
async def assert_MakeFailed(env: Env, nfailed: int, nblocked: int):
    try:
        yield
    except MakeFailed as e:
        if len(e.failed) != nfailed:
            msg = f"Expected {nfailed} failed, got {len(e.failed)}: {e.failed}"
            raise Exception(msg)
        if len(e.blocked) != nblocked:
            msg = f"Expected {nblocked} blocked, got {len(e.blocked)}: {e.blocked}"
            raise Exception(msg)
    except Exception as e:
        raise Exception("unexpected: %s" % e)
