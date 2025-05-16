from collections.abc import AsyncIterator
from collections.abc import Awaitable
from collections.abc import Callable
from collections.abc import Collection
from contextlib import asynccontextmanager
from tempfile import mkdtemp
from typing import Any
from typing import cast
from unittest import SkipTest

from zuper_commons.cmds import ExitCode
from zuper_commons.fs import getcwd
from zuper_commons.test_utils import my_assert_equal
from zuper_commons.types import ZAssertionError
from zuper_commons.types import ZException
from zuper_commons.types import ZValueError
from zuper_utils_asyncio import SyncTaskInterface
from zuper_utils_asyncio import create_sync_task2
from zuper_zapp import async_run_timeout
from zuper_zapp import setup_environment2
from zuper_zapp.utils import with_log_control

from compmake import CacheQueryDB
from compmake import CMJobID
from compmake import CommandFailed
from compmake import ContextImp
from compmake import Job
from compmake import JobInterface
from compmake import MakeFailed
from compmake import StorageFilesystem
from compmake import all_jobs
from compmake import get_job
from compmake import parse_job_list
from compmake import read_rc_files


class Env(JobInterface):
    rootd: str
    sti: SyncTaskInterface
    db: StorageFilesystem
    cc: ContextImp
    cq: CacheQueryDB

    def __init__(self, root, sti: SyncTaskInterface):
        self.rootd = root
        self.sti = sti

    def comp(self, *args: Any, **kwargs: Any) -> Any:
        return self.cc.comp(*args, **kwargs)

    def comp_dynamic(self, *args: Any, **kwargs: Any) -> Any:
        return self.cc.comp_dynamic(*args, **kwargs)

    async def init(self):
        # self.db = StorageFilesystem(self.rootd, compress=True)
        self.cc = ContextImp(self.rootd, name="FromEnv")
        await self.cc.init(self.sti)
        self.db = self.cc.compmake_db

        self.cq = CacheQueryDB(db=self.db)
        self.cc.set_compmake_config("console_status", False)
        await read_rc_files(self.sti, context=self.cc)

    async def aclose(self) -> None:
        await self.cc.aclose()

    async def all_jobs(self):
        """Returns the list of jobs corresponding to the given expression."""
        return sorted(list(all_jobs(self.db)))

    async def get_job(self, job_id: CMJobID) -> Job:
        return get_job(job_id=job_id, db=self.db)

    async def assert_defined_by(self, job_id: CMJobID, expected: list[CMJobID]):
        my_assert_equal((await self.get_job(job_id)).defined_by, expected)

    async def get_jobs(self, expression: str):
        """Returns the list of jobs corresponding to the given expression."""
        cq = CacheQueryDB(self.db)
        with cq.session() as cqs:
            return list(parse_job_list(expression, cqs))

    async def assert_job_uptodate(self, job_id: CMJobID, status: bool):
        res = await self.up_to_date(job_id)
        self.assert_equal(res, status, f"Want {job_id!r} uptodate? {status}")

    def assert_equal[X](self, first: X, second: X, msg: str | None = None):
        my_assert_equal(first, second, msg)

    async def assert_jobs_equal(self, expr: str, jobs: Collection[str], ignore_dyn_reports: bool = True):
        # js = 'not-valid-yet'
        js = await self.get_jobs(expr)
        if ignore_dyn_reports:
            js = [x for x in js if not "dynreports" in x]
        try:
            self.assert_equal_set(js, jobs)
        except:
            print(f"expr {expr!r} -> {js}")
            print("differs from %s" % jobs)
            raise

    def assert_equal_set[X](self, a: Collection[X], b: Collection[X]) -> None:
        sa = set(a)
        sb = set(b)
        if sa != sb:
            raise ZAssertionError("different sets", sa=sa, sb=sb, only_sa=sa - sb, only_sb=sb - sa)

    async def assert_cmd_fail(self, cmds: str) -> None:
        """Executes the (list of) commands and checks it was succesful."""
        print("@ %s     [supposed to fail]" % cmds)
        try:
            await self.batch_command(cmds)
            self.cq.invalidate()

        except CommandFailed:
            pass
        except Exception as e:
            msg = "Command caused exception but not CommandFailed."
            raise ZAssertionError(msg, cmds=cmds) from e
        else:  # pragma: no cover
            msg = "Command did not fail."
            raise ZAssertionError(msg, cmds=cmds)

    async def assert_cmd_success(self, cmds: str) -> None:
        """Executes the (list of) commands and checks it was succesful."""
        print("@ %s" % cmds)
        try:
            await self.batch_command(cmds)
        except MakeFailed as e:
            failed = e.info["failed"]
            print("Detected MakeFailed")
            print("Failed jobs: %s" % failed)
            for job_id in failed:
                await self.cc.interpret_commands_wrap(self.sti, "details %s" % job_id)
            msg = "Command %r failed." % cmds
            raise ZAssertionError(msg) from e
        except Exception as e:
            msg = "Command %r failed." % cmds
            raise ZAssertionError(msg) from e
        # except CommandFailed:
        #     # msg = 'Command %r failed. (res=%s)' % (cmds, res)
        #     raise

        await self.cc.interpret_commands_wrap(self.sti, "check_consistency raise_if_error=1")
        self.cq.invalidate()

    async def batch_command(self, s: str):
        await self.cc.interpret_commands_wrap(self.sti, s)
        # await self.cc.batch_command(self.sti, s)
        self.cq.invalidate()

    async def up_to_date(self, job_id: str) -> bool:
        with self.cq.session() as cqs:
            up, reason, timestamp = cqs.up_to_date(cast(CMJobID, job_id))
        self.sti.logger.info(f"up_to_date({job_id!r}): {up}, {reason!r}, {timestamp}")
        return up

    def session(self):
        return self.cq.session()


async def make_environment(sti: SyncTaskInterface, rootd: str | None = None) -> Env:
    if rootd is None:
        rootd = mkdtemp()
    sti.logger.info(f"Using rootd={rootd!r}")
    env = Env(rootd, sti)
    await env.init()
    return env


@asynccontextmanager
async def environment(sti: SyncTaskInterface, rootd: str | None = None) -> AsyncIterator[Env]:
    env = await make_environment(sti, rootd)
    try:
        yield env
    finally:
        await env.aclose()
        pass


def raise_exit(f):
    def f2():
        ret = f()
        if ret:
            raise ZException(f=f, ret=ret)
            # sys.exit(ret)

    f2.__name__ = f.__name__
    return f2


def run_with_env(f: Callable[[Env], Awaitable[ExitCode | None]]) -> Callable[[], ExitCode | None]:
    if not f.__name__.startswith("test_"):
        msg = 'Better to start test names with "test_".'
        raise ZValueError(msg, f=f, name=f.__name__, qual=f.__qualname__)

    @async_run_timeout(100)
    async def test_main() -> ExitCode:
        async def task(sti: SyncTaskInterface):
            sti.started()
            cwd = getcwd()
            # sti.set_fs(LocalFS(cwd, allow_up=True, sti=sti))

            async with setup_environment2(sti, working_dir=cwd):
                async with with_log_control(False):  # XXX
                    async with environment(sti, rootd=None) as env:
                        try:
                            await f(env)
                        except SkipTest:
                            raise
                        except BaseException as e:
                            # sti.logger.error(traceback.format_exc())
                            # sti.logger.error("these are some stats", all_jobs=await env.all_jobs())

                            raise ZException(all_jobs=await env.all_jobs()) from e

        t = await create_sync_task2(None, task)
        return await t.wait_for_outcome_success_result()

    test_main.__name__ = f.__name__
    test_main.__qualname__ = f.__qualname__
    # noinspection PyUnresolvedReferences
    test_main.__module__ = f.__module__
    # noinspection PyTypeChecker
    return test_main


@asynccontextmanager
async def assert_raises_async(ExceptionType: type[Exception]) -> AsyncIterator[None]:
    try:
        yield
    except ExceptionType:
        pass
    except BaseException as e:
        msg = f"Expected exception {ExceptionType.__name__} but obtained {type(e).__name__}."
        raise ZAssertionError(msg) from e
    else:
        msg = f"Expected exception {ExceptionType.__name__} but none was thrown."
        raise ZAssertionError(
            msg,
        )
