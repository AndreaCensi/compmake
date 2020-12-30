import os
from abc import ABCMeta
from contextlib import asynccontextmanager
from shutil import rmtree
from tempfile import mkdtemp

from aiounittest import AsyncTestCase
from nose.tools import assert_equal

from compmake import (
    CacheQueryDB,
    CommandFailed,
    compmake_main,
    CompmakeConstants,
    get_job,
    Job,
    logger,
    MakeFailed,
    parse_job_list,
    set_compmake_config,
    StorageFilesystem,
)
from compmake.context_imp import ContextImp
from compmake.types import CMJobID
from compmake_tests.utils import Env
from zuper_utils_asyncio import SyncTaskInterface


class CompmakeTest(AsyncTestCase):
    __metaclass__ = ABCMeta

    async def setUp(self):
        self.root0 = mkdtemp()
        self.root = os.path.join(self.root0, "compmake")
        self.db = StorageFilesystem(self.root, compress=True)
        self.cc = ContextImp(db=self.db)
        # don't use '\r'
        set_compmake_config("interactive", False)
        set_compmake_config("console_status", False)

        CompmakeConstants.debug_check_invariants = True
        self.mySetUp()

    async def tearDown(self):
        if True:
            print("not deleting %s" % self.root0)
        else:
            rmtree(self.root0)
        from multiprocessing import active_children

        c = active_children()
        logger.info("active children", c=c)
        if c:
            if True:
                msg = "Still active children"
                logger.warning(msg, c=c)
            else:
                raise Exception(msg)

    # optional init
    # noinspection PyPep8Naming
    def mySetUp(self):
        pass

    # useful
    def comp(self, *args, **kwargs):
        return self.cc.comp(*args, **kwargs)

    async def batch_command(self, sti: SyncTaskInterface, s: str):
        return await self.cc.batch_command(sti, s)

    def get_job(self, job_id: CMJobID) -> Job:
        db = self.cc.get_compmake_db()
        return get_job(job_id=job_id, db=db)

    def get_jobs(self, expression):
        """ Returns the list of jobs corresponding to the given expression. """
        return list(parse_job_list(expression, context=self.cc))

    async def assert_cmd_success(self, sti: SyncTaskInterface, cmds):
        """ Executes the (list of) commands and checks it was succesful. """
        logger.info("@ %s" % cmds)
        try:
            await self.cc.batch_command(sti, cmds)
        except MakeFailed as e:
            logger.info("Detected MakeFailed")
            logger.info("Failed jobs: %s" % e.failed)
            for job_id in e.failed:
                await self.cc.interpret_commands_wrap(sti, "details %s" % job_id)
            raise
        except CommandFailed:
            # msg = 'Command %r failed. (res=%s)' % (cmds, res)
            raise

        await self.cc.interpret_commands_wrap(sti, "check_consistency raise_if_error=1")

    async def assert_cmd_fail(self, sti: SyncTaskInterface, cmds):
        """ Executes the (list of) commands and checks it was succesful. """
        logger.info("@ %s     [supposed to fail]" % cmds)
        try:
            await self.cc.batch_command(sti, cmds)
        except CommandFailed:
            pass
        else:  # pragma: no cover
            msg = "Command %r did not fail." % cmds
            raise Exception(msg)

    async def assert_cmd_success_script(self, sti: SyncTaskInterface, cmd_string: str):
        """ This runs the "compmake_main" script which recreates the DB and
        context from disk. """
        ret = await compmake_main(sti, [self.root, "--nosysexit", "-c", cmd_string])
        assert_equal(ret, 0)

    # useful mcdp_lang_tests
    def assert_defined_by(self, job_id, expected):
        assert_equal(self.get_job(job_id).defined_by, expected)

    def assert_equal_set(self, a, b):
        assert_equal(set(a), set(b))

    def assert_jobs_equal(self, expr: str, jobs, ignore_dyn_reports=True):

        # js = 'not-valid-yet'
        js = self.get_jobs(expr)
        if ignore_dyn_reports:
            js = [x for x in js if not "dynreports" in x]
        try:
            self.assert_equal_set(js, jobs)
        except:
            logger.info(f"expr {expr!r} -> {js}")
            logger.info(f"differs from {jobs}")
            raise

    def assert_job_uptodate(self, job_id, status):
        res = self.up_to_date(job_id)
        assert_equal(res, status, "Want %r uptodate? %s" % (job_id, status))

    def up_to_date(self, job_id) -> bool:

        cq = CacheQueryDB(db=self.db)
        up, reason, timestamp = cq.up_to_date(job_id)
        logger.info(f"up_to_date({job_id!r}): {up}, {reason!r}, {timestamp}")
        return up


@asynccontextmanager
async def assert_MakeFailed(env: Env, nfailed: int, nblocked: int):
    try:
        yield
    except MakeFailed as e:
        if len(e.failed) != nfailed:
            msg = "Expected %d failed, got %d: %s" % (nfailed, len(e.failed), e.failed)
            raise Exception(msg)
        if len(e.blocked) != nblocked:
            msg = "Expected %d blocked, got %d: %s" % (nblocked, len(e.blocked), e.blocked)
            raise Exception(msg)
    except Exception as e:
        raise Exception("unexpected: %s" % e)
