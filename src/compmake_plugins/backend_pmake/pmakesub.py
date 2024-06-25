import asyncio
import gc
import multiprocessing
import os
import signal
import sys
import time
import traceback

from psutil import NoSuchProcess

from compmake import Event

# noinspection PyProtectedMember
from multiprocessing.context import BaseContext, Process
from queue import Empty
from typing import Any, Callable, Literal, Optional, cast
from . import logger
import psutil

from compmake import (
    AsyncResultInterface,
    CMJobID,
    CompmakeBug,
    HostFailed,
    JobFailed,
    JobInterrupted,
    ResultDict,
    parmake_job2_new_process_1,
    result_dict_raise_if_error,
)
from compmake.constants import CANCEL_REASONS
from compmake.registered_events import EVENT_WORKER_JOB_FINISHED
from compmake_utils import setproctitle
from zuper_commons.fs import FilePath, getcwd
from zuper_commons.text import indent, joinlines
from zuper_commons.types import TM, ZAssertionError, ZValueError
from zuper_commons.ui import duration_compact, size_compact
from zuper_utils_asyncio import (
    EveryOnceInAWhile,
    Global,
    SyncTaskInterface,
    get_report_splitters_text,
    get_report_splitters_text_referrers,
    running_tasks,
)
from zuper_utils_timing import TimeInfo
from zuper_zapp import async_run_simple1, setup_environment2
from .parmake_job2_imp import ParmakeJobResult, parmake_job2

__all__ = [
    "PmakeSub",
    "PossibleFuncs",
]

PossibleFuncs = Literal["parmake_job2_new_process_1", "parmake_job2"]

SubStates = Literal["available", "processing", "dead"]


class PmakeSub:
    last: "Optional[PmakeResult]"
    EXIT_TOKEN = "please-exit"
    job_queue: "multiprocessing.Queue[str | tuple[CMJobID, PossibleFuncs, tuple[Any, ...]]]"
    result_queue: "multiprocessing.Queue[ResultDict]"
    _proc: Process
    killed_by_me: bool
    killed_reason: Optional[CANCEL_REASONS]
    state: SubStates
    total_time_processing: float
    total_time_available: float

    def __repr__(self) -> str:
        if self.last is None:
            lasts = ""
        else:
            lasts = f"last={self.last!r}"
        memstats = self.get_mem_usage_pretty()
        return (
            f"PmakeSub({self.name}, nstarted={self.nstarted}, {self.write_log}, proc={self._proc.pid}, "
            f"alive={self._proc.is_alive()}, {lasts}, {memstats})"
        )

    def __init__(
        self,
        *,
        name: str,
        signal_queue: "Optional[multiprocessing.Queue[Any]]",
        event_queue: "Optional[multiprocessing.Queue[Any]]",
        signal_token: str,
        ctx: BaseContext,
        write_log: Optional[FilePath],
        detailed_python_mem_stats: bool,
        job_timeout: Optional[float],
    ):
        self.nstarted = 0
        self.name = name
        self.job_queue = ctx.Queue()
        self.result_queue = ctx.Queue()
        self.event_queue = event_queue
        # print('starting process %s ' % name)
        self.write_log = write_log
        self.job_timeout = job_timeout
        args = (
            self.name,
            self.job_queue,
            self.result_queue,
            signal_queue,
            signal_token,
            write_log,
            detailed_python_mem_stats,
            job_timeout,
            event_queue,
        )
        # logger.info(args=args)
        self.last = None
        self.killed_by_me = False
        self.killed_reason = None
        self._proc = cast(Process, ctx.Process(target=pmake_worker, args=args, name=name, daemon=True))  # type: ignore
        # atexit.register(at_exit_delete, proc=self._proc)
        self._proc.start()
        self.every_once_in_a_while = EveryOnceInAWhile(3)
        self.last_mem_usage = 0
        self.max_mem_usage = 0
        self.last_mem_usage_sampled = 0
        self.pr = psutil.Process(self._proc.pid)
        self.state = "available"
        self.available_since = time.time()
        self.total_time_processing = 0.0
        self.total_time_available = 0.0

    def is_alive(self) -> bool:
        return self._proc.is_alive()

    def terminate_process(self) -> None:
        self.killed_by_me = True
        try:
            self._proc.terminate()
            self._proc.close()
        except:
            pass

    def kill_process(self) -> None:
        self.killed_by_me = True

        parent = psutil.Process(self._proc.pid)
        for child in parent.children(recursive=True):
            logger.debug(f"killing of sub {self.name} child: {child}")
            try:
                child.kill()
            except NoSuchProcess:
                pass

        # noinspection PyBroadException
        try:
            self._proc.kill()
            self._proc.close()
        except:
            pass

        self.pr = None

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

    def is_running(self, job_id: CMJobID) -> bool:
        return self.last is not None and self.last.job_id == job_id

    def apply_async(self, job_id: CMJobID, function: PossibleFuncs, arguments: TM[Any]) -> "PmakeResult":
        if self.state != "available":
            raise ZValueError(f"Cannot apply_async() to not available")
        self.nstarted += 1
        self.job_queue.put((job_id, function, arguments), block=False)
        self.state = "processing"
        self.total_time_available += time.time() - self.available_since
        self.last = PmakeResult(self.result_queue, self, job_id)
        return self.last

    def set_available(self):
        if self.state != "processing":
            raise ZValueError(f"Cannot set_available if not processing")
        self.state = "available"
        self.last.invalid = True
        self.available_since = time.time()
        self.total_time_processing += time.time() - self.last.started
        self.last = None

    def time_since_last(self) -> float:
        now = time.time()
        if self.last is not None:
            return now - self.last.started
        else:
            return now - self.available_since

    def is_available(self) -> bool:
        return self.state == "available"

    def is_processing(self) -> bool:
        return self.state == "processing"

    def get_mem_usage(self, max_delay: float) -> tuple[int, int]:
        now = time.time()
        if now - self.last_mem_usage_sampled > max_delay:
            if self._proc.is_alive():
                try:
                    pr = self.pr.memory_info().rss
                    self.last_mem_usage = pr
                    self.max_mem_usage = max(self.max_mem_usage, pr)
                    self.last_mem_usage_sampled = time.time()
                except:
                    pass
        return self.max_mem_usage, self.last_mem_usage

    def get_cpu_usage(self, max_delay: float) -> float:
        if self._proc.is_alive():
            try:
                return self.pr.cpu_percent(interval=0)
            except:
                return 0.0
        else:
            return 0.0

    def get_mem_usage_pretty(self) -> str:
        mem_stats = self.get_mem_usage(max_delay=3)
        # mem_stats = self.max_mem_usage, self.last_mem_usage
        maxs = size_compact(mem_stats[0])
        curs = size_compact(mem_stats[1])
        mem_stats_s = f"memory stats uss: max: {maxs} cur: {curs}"
        return mem_stats_s


def at_exit_delete(proc: Process) -> None:
    # print(f'terminating process {ps.name} ')
    # ps.terminate()
    # time.sleep(1)
    proc.kill()
    pass


#
#
# def timeout_wrapper(f: Callable[PS, X], *args: PS.args, **kwargs: PS.kwargs) -> X:
#     TIMEOUT = MCDPTestConstants.mcdp_tests_timeout
#     if TIMEOUT is None:
#         return f(*args, **kwargs)
#
#     cons = MCDPTestConstants.mcdp_tests_timeout_consequences
#
#     try:
#         f2 = cast(Callable[PS, X], timeout(TIMEOUT)(f))
#         return f2(*args, **kwargs)
#     except TimeoutError as e:
#         match (cons):
#             case "mark_test_as_skipped":
#                 raise SkipTest(f"Timeout after {TIMEOUT}") from e
#             case "mark_test_as_error":
#                 raise
#             case _ as un:
#                 DPInternalError.assert_never(un)


def _format_dt(dt: float, reference: Optional[float] = None):

    s = f"{duration_compact(dt):10}"
    if reference is not None and reference > dt > 0:
        perc = 100 * dt / reference
        percentage = f"({perc:.1f}%)"
        s += f" {percentage:5}"
    return s


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
    job_timeout: Optional[float],
    event_queue: "Optional[multiprocessing.Queue[Any]]",
):
    try:

        current_name = name
        i = 0
        for i in range(19):
            try:
                os.nice(1)
            except:
                break
        #
        # try:
        #     prev = os.nice(1)
        #
        #     max_nice = 19
        #     if prev < max_nice:
        #         diff = max_nice - prev
        #         os.nice(diff)
        # except Exception:
        #     sti.logger.error("Could not set nice level.", t=traceback.format_exc())
        #     pass
        # sti.logger.info(f"nice: {prev} -> {cur}")

        t_worker_start = time.time()
        total_time_get = 0.0
        total_time_put = 0.0
        total_time_comp = 0.0
        total_time_maintenance = 0.0
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

            # The idea is that the parent will receive it
            signal.signal(signal.SIGINT, signal.SIG_IGN)

            def put_result(x: ResultDict) -> float:
                log("putting result in result_queue..")
                t01 = time.time()
                event_queue.put_nowait(Event(EVENT_WORKER_JOB_FINISHED, worker=name, job_id=job_id))
                result_queue.put(x, block=False)
                log(f"put result in result_queue in {time.time() - t01:.2f} seconds")
                if signal_queue is not None:
                    log("putting result in signal_queue..")
                    t01 = time.time()
                    signal_queue.put(signal_token, block=True)
                    log(f"put result in signal_queue in {time.time() - t0:.2f} seconds")
                log("(done)")
                dt0 = time.time() - t01
                nonlocal total_time_put
                total_time_put += dt0
                return dt0

            time_to_gc = EveryOnceInAWhile(30)
            # noinspection PyBroadException
            memory_tracker: Any
            memory_tracker = None

            job_id: CMJobID = cast(CMJobID, "n/a")  # keep, possibly unbound

            try:
                if detailed_python_mem_stats:
                    from pympler import tracker  # type: ignore

                    memory_tracker = tracker.SummaryTracker()

                while True:
                    total_time = time.time() - t_worker_start

                    sput = _format_dt(total_time_put, total_time)
                    sget = _format_dt(total_time_get, total_time)
                    scomp = _format_dt(total_time_comp, total_time)
                    smant = _format_dt(total_time_maintenance, total_time)
                    unaccounted = total_time - (total_time_comp + total_time_get + total_time_put)
                    sunaccounted = _format_dt(unaccounted, total_time)
                    log(
                        f"worker: total {duration_compact(total_time):10} | comp {scomp}  | get {sget}    | put {sput} | mant "
                        f"{smant}  "
                        f"| unacc "
                        f"{sunaccounted}"
                    )

                    if time_to_gc.now():
                        t0 = time.time()
                        log("gc start")
                        gc.collect()
                        log("gc end")
                        total_time_maintenance += time.time() - t0

                    if detailed_python_mem_stats:
                        t0 = time.time()

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
                        total_time_maintenance += time.time() - t0

                    if detailed_python_mem_stats:
                        t0 = time.time()

                        diff = memory_tracker.format_diff()
                        log(f"Before loading job: \n\n" + joinlines(diff))
                        del diff
                        diff = None
                        total_time_maintenance += time.time() - t0

                    log("Listening for job")
                    t0 = time.time()
                    # event = Event("worker-status", status="waiting-for-job", worker=name)
                    # event_queue.put_nowait(event)

                    try:
                        job = job_queue.get(block=True, timeout=5)
                    except Empty:
                        log("Could not receive anything.")
                        continue
                    dt = time.time() - t0
                    time_to_get_job = dt
                    total_time_get += dt
                    if job == PmakeSub.EXIT_TOKEN:
                        log("Received EXIT_TOKEN.")
                        break

                    log(f"got job: {job} in {time_to_get_job:.2f} seconds")

                    job_id, function_name, arguments = job
                    event_queue.put_nowait(Event("worker-job-started", worker=name, job_id=job_id))

                    arguments += (event_queue,)
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
                    try:
                        t0 = time.time()
                        log(f"creating task...")
                        child = await sti.create_child_task2(job_id, funcwrap, function, arguments)
                        log(f"waiting for task...")

                        pres: ParmakeJobResult = await child.wait_for_outcome_success_result()
                        result = pres.rd
                        log(f"...task finished")

                        # time_to_do_job = time.time() - t0
                        total_time_comp += pres.time_comp

                        if "ti" in result:
                            ti = cast(TimeInfo, result["ti"])
                            log(ti.pretty())
                            result.pop("ti")

                        sti.forget_child(child)
                        del child

                        # log(f"timing: get job = {time_to_get_job:.3f} s, do job = {pres.time_comp:.3f} s")

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
                mye = HostFailed(host="???", job_id=job_id, reason="Uknown exception (not BaseException)", bt="not available")
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
    finally:
        event_queue.put(Event("worker-exiting", worker=name))
        from .pmake_manager import killtree

        killtree()
        event_queue.put(Event("worker-exit", worker=name))
        sys.exit(0)


async def funcwrap(sti: SyncTaskInterface, function: Callable[..., Any], arguments: list[Any]) -> Any:
    await sti.started_and_yield()
    # sti.logger.info("now_running", function=function, arguments=arguments)
    try:
        return await function(sti=sti, args=arguments)
    except:
        sti.logger.error("funcwrap exception")
        raise
    finally:
        sti.logger.info("done")


class PmakeResult(AsyncResultInterface):
    """Wrapper for the async result object obtained by pool.apply_async"""

    result: Optional[ResultDict]
    result_queue: "multiprocessing.Queue[ResultDict]"

    def __init__(self, result_queue: "multiprocessing.Queue[ResultDict]", psub: "PmakeSub", job_id: CMJobID):
        self.result_queue = result_queue
        self.result = None
        self.psub = psub
        self.job_id = job_id
        self.started = time.time()
        self.every_once_in_a_while = EveryOnceInAWhile(5)
        self.invalid = False
        # self.count = 0

    async def get_memory_usage(self, max_delay: float) -> int:
        peak, cur = self.psub.get_mem_usage(max_delay)
        return peak

    def __repr__(self) -> str:
        time_since_started = time.time() - self.started
        return f"<PmakeResult {self.job_id!r} age {time_since_started:.1f}s >"

    def ready(self) -> bool:
        # self.count += 1
        if self.invalid:
            raise ZAssertionError("This result is invalid.")

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

    async def get(self, timeout: float = 0) -> ParmakeJobResult:
        """Raises multiprocessing.TimeoutError"""
        if self.invalid:
            raise ZAssertionError("This result is invalid.")

        if self.result is None:

            if not self.psub.is_alive():
                raise multiprocessing.TimeoutError()

                # print(f'pid = {proc.pid}  alive = {proc.is_alive()}')
            # mem_stats = self.psub.get_mem_usage()
            # maxs = size_compact(mem_stats[0])
            # curs = size_compact(mem_stats[1])
            # mem_stats_s = f'memory stats: max: {maxs} cur: {curs}'
            try:
                # loop = asyncio.get_event_loop()
                # self.result = await loop.run_in_executor(None, lambda: self.result_queue.get(block=True, timeout=timeout))

                self.result = self.result_queue.get(block=True, timeout=timeout)

                # self.result = self.result_queue.get(block=True, timeout=timeout)
            except ValueError:
                # This means that the process was killed
                raise multiprocessing.TimeoutError() from None
            except Empty as e:
                if self.psub.is_alive():
                    raise multiprocessing.TimeoutError() from None

                if self.psub.killed_by_me:
                    msg = f"Process was killed by me.\n"
                    # msg += f'{mem_stats_s}\n'
                    raise multiprocessing.TimeoutError(msg) from None

                exit_code = self.psub._proc.exitcode
                if exit_code is not None:
                    if exit_code == -9:
                        msg = "Exit code -9: Guessing OOM\n"
                    else:
                        msg = f"Process died unexpectedly with code {exit_code}\n"
                else:
                    msg = f"Interrupt: Process died unexpectedly but no exit code is available\n"

                # msg += f'{mem_stats_s}\n'

                msg += f"\n log at {self.psub.write_log}"
                msg += f"\n sub {self.psub!r}"
                msg += f"\n sub {self.psub.__dict__!r}"
                raise JobFailed(
                    job_id=self.job_id,
                    reason=msg,
                    bt="not available",
                    deleted_jobs=[],
                ) from None

        r: ResultDict = self.result
        rd = result_dict_raise_if_error(r)
        return ParmakeJobResult(rd, time_other=0, time_comp=0, time_total=0)
