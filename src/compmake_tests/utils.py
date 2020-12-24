from contextlib import asynccontextmanager
from tempfile import mkdtemp
from typing import AsyncIterator, cast, TypeVar

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
    StorageFilesystem,
)
from zuper_commons.types import ZAssertionError
from zuper_utils_asyncio import async_main_sti, SyncTaskInterface

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
        self.cq = CacheQueryDB(db=self.db)

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
        assert_equal(set(a), set(b))

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

    async def batch_command(self, s):
        await self.cc.batch_command(self.sti, s)

    async def up_to_date(self, job_id: str) -> bool:
        up, reason, timestamp = self.cq.up_to_date(cast(CMJobID, job_id))
        print("up_to_date(%r): %s, %r, %s" % (job_id, up, reason, timestamp))
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


def run_test_with_env(f):
    @async_main_sti(None, main_function=False)
    async def f2(sti: SyncTaskInterface):
        sti.started()

        async with environment(sti) as env:
            await f(env)

    f2.__name__ = f.__name__
    return f2


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
