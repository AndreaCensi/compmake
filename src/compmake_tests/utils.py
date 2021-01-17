import os
import traceback
from contextlib import asynccontextmanager
from tempfile import mkdtemp
from typing import AsyncIterator, Awaitable, Callable, cast, TypeVar

from nose.tools import assert_equal

from compmake import (
    all_jobs,
    CacheQueryDB,
    CMJobID,
    CommandFailed,
    ContextImp,
    get_job,
    Job,
    MakeFailed,
    parse_job_list,
    read_rc_files,
    StorageFilesystem,
)
from zuper_commons.cmds import ExitCode
from zuper_commons.types import ZAssertionError, ZException, ZValueError
from zuper_utils_asyncio import async_run_timeout, create_sync_task2, setup_environment2, SyncTaskInterface
from zuper_utils_asyncio.utils import with_log_control

X = TypeVar("X")


class Env:
    rootd: str
    sti: SyncTaskInterface
    db: StorageFilesystem
    cc: ContextImp
    cq: CacheQueryDB

    def __init__(self, root, sti: SyncTaskInterface):
        self.rootd = root
        self.sti = sti

    def comp(self, *args, **kwargs):
        return self.cc.comp(*args, **kwargs)

    def comp_dynamic(self, *args, **kwargs):
        return self.cc.comp_dynamic(*args, **kwargs)

    async def init(self):
        self.db = StorageFilesystem(self.rootd, compress=True)
        self.cc = ContextImp(self.db)
        await self.cc.init()
        self.cq = CacheQueryDB(db=self.db)
        self.cc.set_compmake_config("console_status", False)
        await read_rc_files(self.sti, context=self.cc)

    async def all_jobs(self):
        """ Returns the list of jobs corresponding to the given expression. """
        # db = StorageFilesystem(self.env, compress=True)
        return sorted(list(all_jobs(self.db)))

    async def get_job(self, job_id) -> Job:
        return get_job(job_id=job_id, db=self.db)

    async def assert_defined_by(self, job_id, expected):
        assert_equal((await self.get_job(job_id)).defined_by, expected)

    async def get_jobs(self, expression: str):
        """ Returns the list of jobs corresponding to the given expression. """
        return list(parse_job_list(expression, context=self.cc))

    async def assert_job_uptodate(self, job_id, status):
        res = await self.up_to_date(job_id)
        self.assert_equal(res, status, "Want %r uptodate? %s" % (job_id, status))

    def assert_equal(self, first: X, second: X, msg: str = None):
        assert_equal(first, second, msg)

    async def assert_jobs_equal(self, expr: str, jobs, ignore_dyn_reports=True):

        # js = 'not-valid-yet'
        js = await self.get_jobs(expr)
        if ignore_dyn_reports:
            js = [x for x in js if not "dynreports" in x]
        try:
            self.assert_equal_set(js, jobs)
        except:
            print("expr %r -> %s" % (expr, js))
            print("differs from %s" % jobs)
            raise

    def assert_equal_set(self, a, b):
        sa = set(a)
        sb = set(b)
        if sa != sb:
            raise ZAssertionError("different sets", sa=sa, sb=sb, only_sa=sa - sb, only_sb=sb - sa)

    async def assert_cmd_fail(self, cmds):
        """ Executes the (list of) commands and checks it was succesful. """
        print("@ %s     [supposed to fail]" % cmds)
        try:
            await self.batch_command(cmds)
        except CommandFailed:
            pass
        except Exception as e:
            msg = "Command caused exception but not CommandFailed."
            raise ZAssertionError(msg, cmds=cmds) from e
        else:  # pragma: no cover
            msg = "Command did not fail."
            raise ZAssertionError(msg, cmds=cmds)

    async def assert_cmd_success(self, cmds):
        """ Executes the (list of) commands and checks it was succesful. """
        print("@ %s" % cmds)
        try:
            await self.batch_command(cmds)
        except MakeFailed as e:
            print("Detected MakeFailed")
            print("Failed jobs: %s" % e.failed)
            for job_id in e.failed:
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

    async def batch_command(self, s: str):
        await self.cc.interpret_commands_wrap(self.sti, s)
        # await self.cc.batch_command(self.sti, s)

    async def up_to_date(self, job_id: str) -> bool:
        up, reason, timestamp = self.cq.up_to_date(cast(CMJobID, job_id))
        self.sti.logger.info("up_to_date(%r): %s, %r, %s" % (job_id, up, reason, timestamp))
        return up


async def make_environment(sti: SyncTaskInterface, rootd: str = None) -> Env:
    if rootd is None:
        rootd = mkdtemp()
    env = Env(rootd, sti)
    await env.init()
    return env


@asynccontextmanager
async def environment(sti: SyncTaskInterface, rootd: str = None) -> AsyncIterator[Env]:
    env = await make_environment(sti, rootd)
    try:
        yield env
    finally:
        pass


def raise_exit(f):
    def f2():
        ret = f()
        if ret:
            raise ZException(f=f, ret=ret)
            # sys.exit(ret)

    f2.__name__ = f.__name__
    return f2


def run_with_env(f: Callable[[Env], Awaitable[ExitCode]]) -> Callable[[], ExitCode]:
    if not f.__name__.startswith("test_"):
        msg = 'Better to start test names with "test_".'
        raise ZValueError(msg, f=f, name=f.__name__, qual=f.__qualname__)

    @async_run_timeout(100)
    async def test_main() -> ExitCode:
        async def task(sti: SyncTaskInterface):
            sti.started()
            cwd = os.getcwd()
            # sti.set_fs(LocalFS(cwd, allow_up=True, sti=sti))

            async with setup_environment2(sti, working_dir=cwd):

                async with with_log_control(False):  # XXX
                    async with environment(sti) as env:
                        try:
                            res = await f(env)
                        except BaseException:

                            sti.logger.error(traceback.format_exc())
                            sti.logger.error("these are some stats", all_jobs=await env.all_jobs())

                            raise ZException(traceback.format_exc())

        t = await create_sync_task2(None, task)
        return await t.wait_for_outcome_success_result()

    test_main.__name__ = f.__name__
    test_main.__qualname__ = f.__qualname__
    # noinspection PyUnresolvedReferences
    test_main.__module__ = f.__module__
    return test_main


@asynccontextmanager
async def assert_raises_async(ExceptionType):
    try:
        yield
    except ExceptionType:
        pass
    except BaseException as e:
        msg = f"Expected exception {ExceptionType.__name__} but obtained {type(e).__name__}."
        raise ZAssertionError(msg) from e
    else:
        msg = f"Expected exception {ExceptionType.__name__} but none was thrown."
        raise ZAssertionError(msg,)
