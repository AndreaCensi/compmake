import subprocess
import sys
from contextlib import asynccontextmanager
from typing import cast

from compmake import MakeFailed

from .utils import Env


def test_parallel_default_uses_available_cpus() -> None:
    """The default follows joblib's available CPU count rather than host CPUs."""
    code = """
from unittest.mock import patch
with patch('joblib.cpu_count', return_value=3):
    from compmake.state import get_compmake_config0
    actual = get_compmake_config0('max_parallel_jobs')
    if actual != 3:
        raise AssertionError(f'Expected 3 available CPUs, got {actual}')
"""
    subprocess.run([sys.executable, "-c", code], check=True)


@asynccontextmanager
async def assert_MakeFailed(env: Env, nfailed: int, nblocked: int):
    try:
        yield
    except MakeFailed as e:
        found_failed = cast(list[str], e.info["failed"])
        found_blocked = cast(list[str], e.info["blocked"])
        if len(found_failed) != nfailed:
            msg = f"Expected {nfailed} failed, got {len(found_failed)}: {found_failed}"
            raise Exception(msg)
        if len(found_blocked) != nblocked:
            msg = f"Expected {nblocked} blocked, got {len(found_blocked)}: {found_blocked}"
            raise Exception(msg)
    except Exception as e:
        raise Exception("unexpected: %s" % e)
