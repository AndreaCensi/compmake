import gc
import multiprocessing
import signal
import sys
import time
import traceback

# noinspection PyProtectedMember
from multiprocessing.context import BaseContext, Process
from queue import Empty
from typing import Any, Callable, cast, Literal, Optional, Tuple

from compmake import (
    AsyncResultInterface,
    CMJobID,
    CompmakeBug,
    HostFailed,
    JobFailed,
    JobInterrupted,
    OKResult,
    parmake_job2_new_process_1,
    result_dict_raise_if_error,
    ResultDict,
)
from compmake_utils import setproctitle
from zuper_commons.fs import FilePath, getcwd
from zuper_commons.text import indent, joinlines
from zuper_utils_asyncio import (
    EveryOnceInAWhile,
    get_report_splitters_text,
    get_report_splitters_text_referrers,
    running_tasks,
    SyncTaskInterface,
)
from zuper_utils_asyncio.sync_task_imp import Global
from zuper_utils_timing import TimeInfo
from zuper_zapp import async_run_simple1, setup_environment2
from .parmake_job2_imp import parmake_job2

__all__ = [
    "PmakeSub",
    "PossibleFuncs",
]

import atexit

PossibleFuncs = Literal["parmake_job2_new_process_1", "parmake_job2"]


class PmakeSub:
    last: "Optional[PmakeResult]"
    EXIT_TOKEN = "please-exit"
    job_queue: "multiprocessing.Queue[str | tuple[CMJobID, PossibleFuncs, Tuple[Any, ...]]]"
    result_queue: "multiprocessing.Queue[ResultDict]"
    _proc: Process
    killed_by_me: bool

    def __repr__(self) -> str:
        return (
            f"PmakeSub({self.name}, {self.write_log}, proc={self._proc.pid}, alive="
            f"{self._proc.is_alive()})"
        )

    def __init__(
        self,
        name: str,
        signal_queue: "Optional[multiprocessing.Queue[Any]]",
        signal_token: str,
        ctx: BaseContext,
        write_log: Optional[FilePath],
        detailed_python_mem_stats: bool,
    ):
        self.name = name
        self.job_queue = ctx.Queue()
        self.result_queue = ctx.Queue()
        # print('starting process %s ' % name)
        self.write_log = write_log
        args = (
            self.name,
            self.job_queue,
            self.result_queue,
            signal_queue,
            signal_token,
            write_log,
            detailed_python_mem_stats,
        )
        # logger.info(args=args)
        self._proc = cast(Process, ctx.Process(target=pmake_worker, args=args, name=name))  # type: ignore
        atexit.register(at_exit_delete, proc=self._proc)
        self._proc.start()
        self.last = None
        self.killed_by_me = False

    def is_alive(self) -> bool:
        return self._proc.is_alive()

    def terminate_process(self) -> None:
        self.killed_by_me = True
        try:
            self._proc.terminate()
        except:
            pass

    def kill_process(self) -> None:
        self.killed_by_me = True
        # noinspection PyBroadException
        try:
            self._proc.kill()
        except:
            pass

    def terminate(self) -> None:
        # noinspection PyBroadException
        try:
            self.job_queue.put(PmakeSub.EXIT_TOKEN)
            self.job_queue.close()
            self.result_queue.close()
        except:
            pass
        # self.proc.terminate()
        # self.job_queue = None
        # self.result_queue = None

    def apply_async(
        self, job_id: CMJobID, function: PossibleFuncs, arguments: Tuple[Any, ...]
    ) -> "PmakeResult":
        self.job_queue.put((job_id, function, arguments))
        self.last = PmakeResult(self.result_queue, self, job_id)
        return self.last


def at_exit_delete(proc: Process) -> None:
    # print(f'terminating process {ps.name} ')
    # ps.terminate()
    # time.sleep(1)
    proc.kill()


@async_run_simple1
async def pmake_worker(
    sti: SyncTaskInterface,
    name: str,
    job_queue: "multiprocessing.Queue[str | tuple[CMJobID, Callable[..., Any], list[Any]]]",
    result_queue: "multiprocessing.Queue[ResultDict]",
    signal_queue: "Optional[multiprocessing.Queue[Any]]",
    signal_token: str,
    write_log: Optional[FilePath],
    detailed_python_mem_stats: bool,
):
    current_name = name

    if write_log:
        sys.stderr = sys.stdout = f = open(write_log, "w", buffering=1)  # 1 = line buffered

        def log(s: str):
            f.write(f"{current_name}: {s}\n")
            f.flush()

    else:

        def log(s: str):
            print(f"{current_name}: {s}")
            pass

    log("started pmake_worker()")
    setproctitle(f"compmake:{current_name}")
    async with setup_environment2(sti, getcwd()):
        await sti.started_and_yield()
        # logger.info(f"pmake_worker forked at process {os.getpid()}")
        from coverage import process_startup  # type: ignore

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

        # write_log = None
        # warnings.warn('remove above')

        log("started pmake_worker()")
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        def put_result(x: ResultDict) -> float:
            log("putting result in result_queue..")
            t01 = time.time()
            result_queue.put(x, block=True)
            log(f"put result in result_queue in {time.time() - t01:.2f} seconds")
            if signal_queue is not None:
                log("putting result in signal_queue..")
                t01 = time.time()
                signal_queue.put(signal_token, block=True)
                log(f"put result in signal_queue in {time.time() - t0:.2f} seconds")
            log("(done)")
            return time.time() - t01

        time_to_gc = EveryOnceInAWhile(120)
        # noinspection PyBroadException
        memory_tracker: Any
        memory_tracker = None

        job_id: CMJobID = cast(CMJobID, "n/a")  # keep, possibly unbound

        try:
            if detailed_python_mem_stats:
                from pympler import tracker  # type: ignore

                memory_tracker = tracker.SummaryTracker()

            while True:
                if time_to_gc.now():
                    log("gc start")
                    gc.collect()
                    log("gc end")

                if detailed_python_mem_stats:
                    log("detailed_python_mem_stats... ")

                    # log('all objects...')

                    # all_objects = muppy.get_objects()
                    # log('summarize...')
                    # sum1 = summary.summarize(all_objects)
                    # log('format...')
                    # res = joinlines(format_(sum1, limit=50))
                    # del all_objects
                    # del sum1
                    # sum1 = all_objects = None
                    # log(f"Report pmakeworker {name} IDLE " + "\n\n" + res)
                    log("splitter_...")
                    log(get_report_splitters_text())
                    log(get_report_splitters_text_referrers())

                    log("tasks...")
                    active_tasks = ["-".join(k) for k in Global.active]

                    log(f"{len(active_tasks)} active STI tasks: {active_tasks}")
                    running = [" - " + _.get_name() + f" done = {_.done()}" for _ in running_tasks]
                    log(f"{len(running_tasks)} active create_task:" + "\n" + joinlines(running))
                    del running, active_tasks

                if detailed_python_mem_stats:
                    diff = memory_tracker.format_diff()
                    log(f"Before loading job: \n\n" + joinlines(diff))
                    del diff
                    diff = None

                log("Listening for job")
                t0 = time.time()
                try:
                    job = job_queue.get(block=True, timeout=5)
                except Empty:
                    log("Could not receive anything.")
                    continue
                time_to_get_job = time.time() - t0

                if job == PmakeSub.EXIT_TOKEN:
                    log("Received EXIT_TOKEN.")
                    break

                log(f"got job: {job} in {time_to_get_job:.2f} seconds")

                job_id, function_name, arguments = job

                funcs: dict[str, Any] = {
                    "parmake_job2_new_process_1": parmake_job2_new_process_1,
                    "parmake_job2": parmake_job2,
                }
                function = funcs[function_name]
                if detailed_python_mem_stats:
                    diff = memory_tracker.format_diff()
                    log(f"Diff after loading params for {job_id}: \n\n" + joinlines(diff))
                    del diff
                    diff = None

                current_name = f"{name}:{job_id}"
                setproctitle(f"compmake:{current_name}")
                # logger.info(job=job)
                # print(job)
                # print(inspect.signature(function))
                try:
                    # print('arguments: %s' % str(arguments))
                    t0 = time.time()
                    log(f"creating task...")
                    child = await sti.create_child_task2(job_id, funcwrap, function, arguments)
                    log(f"waiting for task...")

                    result: ResultDict = await child.wait_for_outcome_success_result()
                    log(f"...task finished")
                    if "ti" in result:
                        ti = cast(TimeInfo, result["ti"])
                        log(ti.pretty())
                        result.pop("ti")
                    time_to_do_job = time.time() - t0
                    sti.forget_child(child)
                    del child

                    log(f"timing: get job = {time_to_get_job:.3f} s, do job = {time_to_do_job:.3f} s")

                    # result = await function(sti=sti, args=arguments)
                    # result = function(args=arguments)
                except JobFailed as e:
                    log("Job failed, putting notice.")
                    log(f"result: {e}")  # debug
                    put_result(e.get_result_dict())
                    del e
                except JobInterrupted as e:
                    log("Job interrupted, putting notice.")
                    put_result(dict(abort=str(e)))  # XXX
                    del e
                except CompmakeBug as e:  # XXX :to finish
                    log("CompmakeBug")
                    put_result(e.get_result_dict())
                    del e

                except BaseException:
                    log(f"uncaught error: {job}")
                    raise
                else:
                    log(f"result: {result}")
                    put_result(result)
                    del result
                finally:
                    child = None
                    function = None
                    arguments = None

                del arguments, job
                if detailed_python_mem_stats:
                    import lxml
                    import lxml.etree
                    from pympler import muppy, summary, tracker
                    from pympler.summary import format_

                    log("cleaning lxml error log...")
                    lxml.etree.clear_error_log()
                    log("gc.collect()...")

                    gc.collect()
                    log("detailed_python_mem_stats... ")

                    log("memory tracker diff... ")
                    diff = memory_tracker.format_diff()
                    log(f"Diff after {job_id}: \n\n" + joinlines(diff))

                log("...done.")
                current_name = f"{name}:idle"
                setproctitle(f"compmake:{current_name}")

                # except KeyboardInterrupt: pass
        except BaseException:
            reason = "aborted because of uncaptured:\n" + indent(traceback.format_exc(), "| ")
            mye = HostFailed(host="???", job_id=job_id, reason=reason, bt=traceback.format_exc())
            log(str(mye))
            put_result(mye.get_result_dict())
        except:  # XXX: can this happen?
            mye = HostFailed(
                host="???", job_id=job_id, reason="Uknown exception (not BaseException)", bt="not available"
            )
            log(str(mye))
            put_result(mye.get_result_dict())
            log("(put)")

        if signal_queue is not None:
            signal_queue.close()
        result_queue.close()

        log("memory dump")

        if memory_tracker is not None:
            from pympler import muppy, summary, tracker
            from pympler.summary import format_

            all_objects = muppy.get_objects()
            sum1 = summary.summarize(all_objects)
            res = joinlines(format_(sum1, limit=50))
            log(f"Report for END of pmakeworker {name}" + "\n\n" + res)

        if cov:
            log("saving coverage")
            # noinspection PyProtectedMember
            cov._atexit()  # type: ignore
            log("saved coverage")

        log("clean exit.")


async def funcwrap(sti: SyncTaskInterface, function: Callable[..., Any], arguments: list[Any]) -> Any:
    await sti.started_and_yield()
    sti.logger.info("now_running", function=function, arguments=arguments)
    try:
        return await function(sti=sti, args=arguments)
    except:
        sti.logger.error("funcwrap", tb=traceback.format_exc())
        raise


class PmakeResult(AsyncResultInterface):
    """Wrapper for the async result object obtained by pool.apply_async"""

    result: Optional[ResultDict]
    result_queue: "multiprocessing.Queue[ResultDict]"

    def __init__(self, result_queue: "multiprocessing.Queue[ResultDict]", psub: "PmakeSub", job_id: CMJobID):
        self.result_queue = result_queue
        self.result = None
        self.psub = psub
        self.job_id = job_id
        # self.count = 0

    def ready(self) -> bool:
        # self.count += 1

        if self.result is not None:
            return True

        if not self.psub.is_alive():
            return True  # in get() we do the handling
            # msg = f"Process exited unexpectedly with code {proc.exitcode}"
            # msg += f'\n log at {self.psub.write_log}'
            # raise HostFailed(self.psub.name, job_id=self.job_id, reason=msg, bt="not available")

        try:
            self.result = self.result_queue.get(block=False)
        except Empty:
            # if self.count > 1000 and self.count % 100 == 0:
            # print('ready()?  still waiting on %s' % str(self.job))
            return False
        else:
            return True

    async def get(self, timeout: float = 0) -> OKResult:
        """Raises multiprocessing.TimeoutError"""
        if self.result is None:
            # print(f'pid = {proc.pid}  alive = {proc.is_alive()}')

            try:
                self.result = self.result_queue.get(block=True, timeout=timeout)
            except Empty as e:
                if not self.psub.killed_by_me:
                    if not self.psub.is_alive():
                        msg = f"Interrupt: Process died unexpectedly with code {self.psub._proc.exitcode}"
                        msg += f"\n log at {self.psub.write_log}"
                        msg += f"\n sub {self.psub!r}"
                        msg += f"\n sub {self.psub.__dict__!r}"
                        raise JobFailed(
                            self.psub.name,
                            job_id=self.job_id,
                            reason=msg,
                            bt="not available",
                            deleted_jobs=[],
                        ) from None

                raise multiprocessing.TimeoutError(e)

        r: ResultDict = self.result
        return result_dict_raise_if_error(r)
