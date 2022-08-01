import gc
import multiprocessing
import signal
import traceback

# noinspection PyProtectedMember
from multiprocessing.context import BaseContext
from queue import Empty
from typing import Any, Callable, Optional

import lxml
import lxml.etree
from pympler import muppy, summary, tracker
from pympler.summary import format_

from compmake import (
    AsyncResultInterface,
    CMJobID,
    CompmakeBug,
    HostFailed,
    JobFailed,
    JobInterrupted,
    OKResult,
    result_dict_raise_if_error,
    ResultDict,
)
from compmake_utils import setproctitle
from zuper_commons.fs import FilePath, getcwd
from zuper_commons.text import indent, joinlines
from zuper_utils_asyncio import get_report_splitters_text, running_tasks, SyncTaskInterface
from zuper_utils_asyncio.splitter_utils import get_report_splitters_text_referrers
from zuper_utils_asyncio.sync_task_imp import Global
from zuper_zapp import async_run_simple1, setup_environment2

__all__ = [
    "PmakeSub",
]


class PmakeSub:
    last: "Optional[PmakeResult]"
    EXIT_TOKEN = "please-exit"
    job_queue: "Optional[multiprocessing.Queue[str | tuple[CMJobID, Callable[..., Any], list[Any]]]]"
    result_queue: "Optional[multiprocessing.Queue[ResultDict]]"

    def __init__(
        self,
        name: str,
        signal_queue: "Optional[multiprocessing.Queue]",
        signal_token: str,
        ctx: BaseContext,
        write_log: Optional[FilePath] = None,
    ):
        self.name = name
        self.job_queue = ctx.Queue()
        self.result_queue = ctx.Queue()
        # print('starting process %s ' % name)

        args = (self.name, self.job_queue, self.result_queue, signal_queue, signal_token, write_log)
        # logger.info(args=args)
        self.proc = ctx.Process(
            target=pmake_worker,
            args=args,
            name=name,
        )
        self.proc.start()
        self.last = None

    def terminate(self) -> None:
        self.job_queue.put(PmakeSub.EXIT_TOKEN)
        self.job_queue.close()
        self.result_queue.close()
        self.job_queue = None
        self.result_queue = None

    def apply_async(self, job_id: CMJobID, function, arguments) -> "PmakeResult":
        self.job_queue.put((job_id, function, arguments))
        self.last = PmakeResult(self.result_queue)
        return self.last


@async_run_simple1
async def pmake_worker(
    sti: SyncTaskInterface,
    name: str,
    job_queue: "multiprocessing.Queue[str | tuple[CMJobID, Callable[..., Any], list[Any]]]",
    result_queue: "multiprocessing.Queue[ResultDict]",
    signal_queue: "Optional[multiprocessing.Queue]",
    signal_token: str,
    write_log: Optional[FilePath] = None,
):
    current_name = name
    setproctitle(f"compmake:{current_name}")
    async with setup_environment2(sti, getcwd()):
        await sti.started_and_yield()
        # logger.info(f"pmake_worker forked at process {os.getpid()}")
        from coverage import process_startup

        if hasattr(process_startup, "coverage"):
            # logger.info("Detected coverage wanted.")
            delattr(process_startup, "coverage")
            cov = process_startup()
            if cov is None:
                pass
                # logger.warning("Coverage did not start.")
            else:
                pass
                # logger.info("Coverage started successfully.")
        else:
            # logger.info("Not detected coverage need.")
            cov = None

        if write_log:
            f = open(write_log, "w")

            def log(s: str):
                f.write(f"{current_name}: {s}\n")
                f.flush()

        else:

            def log(s: str):
                # print(f"{current_name}: {s}")
                pass

        log("started pmake_worker()")
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        def put_result(x: ResultDict) -> None:
            log("putting result in result_queue..")
            result_queue.put(x, block=True)
            if signal_queue is not None:
                log("putting result in signal_queue..")
                signal_queue.put(signal_token, block=True)
            log("(done)")

        try:
            memory_tracker = tracker.SummaryTracker()
            job_id = "none yet"
            while True:
                lxml.etree.clear_error_log()
                gc.collect()

                diff = memory_tracker.format_diff()
                all_objects = muppy.get_objects()
                sum1 = summary.summarize(all_objects)
                res = joinlines(format_(sum1, limit=50))
                log(f"Report pmakeworker {name} IDLE " + "\n\n" + res)
                log(get_report_splitters_text())
                log(get_report_splitters_text_referrers())
                log(f"Diff after {job_id}: \n\n" + joinlines(diff))

                active_tasks = ["-".join(k) for k in Global.active]

                log(f"{len(active_tasks)} active STI tasks: {active_tasks}")
                log(f"{len(running_tasks)} active create_task: {running_tasks}")

                log("Listening for job")
                try:
                    job = job_queue.get(block=True, timeout=5)
                except Empty:
                    log("Could not receive anything.")
                    continue
                if job == PmakeSub.EXIT_TOKEN:
                    log("Received EXIT_TOKEN.")
                    break

                log(f"got job: {job}")

                job_id, function, arguments = job

                current_name = f"{name}:{job_id}"
                setproctitle(f"compmake:{current_name}")
                # logger.info(job=job)
                # print(job)
                # print(inspect.signature(function))
                try:
                    # print('arguments: %s' % str(arguments))
                    child = await sti.create_child_task2(job_id, funcwrap, function, arguments)
                    result = await child.wait_for_outcome_success_result()
                    # result = await function(sti=sti, args=arguments)
                    # result = function(args=arguments)
                except JobFailed as e:
                    log("Job failed, putting notice.")
                    log(f"result: {e}")  # debug
                    put_result(e.get_result_dict())
                except JobInterrupted as e:
                    log("Job interrupted, putting notice.")
                    put_result(dict(abort=str(e)))  # XXX
                except CompmakeBug as e:  # XXX :to finish
                    log("CompmakeBug")
                    put_result(e.get_result_dict())
                except BaseException as e:
                    log(f"uncaught error: {job}")
                    raise
                else:
                    log(f"result: {result}")
                    put_result(result)
                    del result

                log("...done.")
                current_name = f"{name}:idle"
                setproctitle(f"compmake:{current_name}")

                # except KeyboardInterrupt: pass
        except BaseException as e:
            reason = "aborted because of uncaptured:\n" + indent(traceback.format_exc(), "| ")
            mye = HostFailed(host="???", job_id="???", reason=reason, bt=traceback.format_exc())
            log(str(mye))
            put_result(mye.get_result_dict())
        except:
            mye = HostFailed(
                host="???", job_id="???", reason="Uknown exception (not BaseException)", bt="not available"
            )
            log(str(mye))
            put_result(mye.get_result_dict())
            log("(put)")

        if signal_queue is not None:
            signal_queue.close()
        result_queue.close()
        log("saving coverage")

        all_objects = muppy.get_objects()
        sum1 = summary.summarize(all_objects)
        res = joinlines(format_(sum1, limit=50))
        log(f"Report for END of pmakeworker {name}" + "\n\n" + res)

        if cov:
            # noinspection PyProtectedMember
            cov._atexit()
        log("saved coverage")

        log("clean exit.")


async def funcwrap(sti: SyncTaskInterface, function: Callable[..., Any], arguments: list) -> Any:
    sti.started()
    return await function(sti=sti, args=arguments)


class PmakeResult(AsyncResultInterface):
    """Wrapper for the async result object obtained by pool.apply_async"""

    result: Optional[ResultDict]

    def __init__(self, result_queue):
        self.result_queue = result_queue
        self.result = None
        # self.count = 0

    def ready(self):
        # self.count += 1
        try:
            self.result = self.result_queue.get(block=False)
        except Empty:
            # if self.count > 1000 and self.count % 100 == 0:
            # print('ready()?  still waiting on %s' % str(self.job))
            return False
        else:
            return True

    async def get(self, timeout=0) -> OKResult:
        """Raises multiprocessing.TimeoutError"""
        if self.result is None:
            try:
                self.result = self.result_queue.get(block=True, timeout=timeout)
            except Empty as e:
                raise multiprocessing.TimeoutError(e)
        r: ResultDict = self.result
        return result_dict_raise_if_error(r)
