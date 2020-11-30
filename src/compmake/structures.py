"""
    A Job represents the computation as passed by the user.
    It contains only the "action" but not the state.
    (The state of the computation is represented by a Cache object.)

    A Cache object can be in one of the following states:

    *) non-existent / or NOT_STARTED
       (no difference between these states)

    *) IN_PROGRESS: The yielding mechanism is taking care of
       the incremental computation.

       computation:  current computation
       user_object:  None / invalid
       timestamp:    None / timestamp
       tmp_result:   set to the temporary result (if any)

       In this state, we also publish a progress report.

    *) DONE:  The computation has been completed

       computation:  current computation
       user_object: the result of the computation
       timestamp:   when computation was completed
       timetaken:   time taken by the computation
       tmp_result:  None


    *) FAILED
       The computation has failed for some reason

       computation:  failed computation

    Note that user_object and tmp_result are stored separately
    from the Cache element.

    DB Layout:

        'job_id:computation'       Job object
        'job_id:cache'             Cache object
        'job_id:user_object'       Result of the computation
        'job_id:user_object_tmp'



    Up-to-date or not?
    =================

    Here we have to be careful because of the fact that we have
    the special state MORE_REQUESTED.
    Is it a computation done if MORE_REQUESTED? Well, we could say
    no, because when more is completed, the parents will need to be
    redone. However, the use case is that:
    1) you do the all computation
    2) you explicity ask MORE for some targets
    3) you explicitly ask to redo the parents of those targets
    Therefore, a MORE_REQUESTED state is considered as uptodate.


"""
from dataclasses import dataclass
from typing import Dict, List, NewType, Optional, Set, Tuple, Union

from zuper_commons.types import describe_value
from zuper_commons.ui import duration_compact

from .utils.pickle_frustration import pickle_main_context_save

__all__ = [
    "Promise",
    "Job",
    "Cache",
    "CMJobID",
    "DBKey",
]

CMJobID = NewType("CMJobID", str)
DBKey = NewType("DBKey", str)


@dataclass
class Promise:
    job_id: CMJobID


class Job:
    job_id: CMJobID
    children: Set
    parents: Set
    needs_conntext: bool
    defined_by: List[CMJobID]
    dynamic_children: dict
    pickle_main_context: object
    command_desc: str

    def __init__(
        self,
        job_id: CMJobID,
        children: Set[CMJobID],
        command_desc: str,
        needs_context: bool = False,
        defined_by: List[CMJobID] = None,
    ):
        """

            needs_context: new facility for dynamic jobs
            defined_by: name of jobs defining this job dynamically
                        This is the stack of jobs. 'root' is the first.

            children: the direct dependencies
        """
        self.job_id = job_id
        self.children = set(children)
        self.command_desc = command_desc
        self.parents = set()
        self.needs_context = needs_context
        self.defined_by = defined_by
        assert len(defined_by) >= 1, defined_by
        assert defined_by[0] == "root", defined_by
        # str -> set(str), where the key is one
        # of the direct children
        self.dynamic_children = {}

        self.pickle_main_context = pickle_main_context_save()


def same_computation(jobargs1, jobargs2):
    """ Returns boolean, string tuple """
    cmd1, args1, kwargs1 = jobargs1
    cmd2, args2, kwargs2 = jobargs2

    equal_command = cmd1 == cmd2
    equal_args = args1 == args2
    equal_kwargs = kwargs1 == kwargs2

    equal = equal_args and equal_kwargs and equal_command
    if not equal:
        reason = ""

        if not equal_command:
            reason += "* function changed \n"
            reason += f"  - old: {cmd1} \n"
            reason += f"  - new: {cmd2} \n"

            # TODO: can we check the actual code?

        warn = " (or you did not implement proper __eq__)"
        if len(args1) != len(args2):
            reason += f"* different number of arguments ({len(args1)} -> {len(args2)})\n"
        else:
            for i, ob in enumerate(args1):
                if ob != args2[i]:
                    reason += f"* arg #{i} changed {warn} \n"
                    reason += f"  - old: {describe_value(ob)}\n"
                    reason += f"  - old: {describe_value(args2[i])}\n"

        for key, value in kwargs1.items():
            if key not in kwargs2:
                reason += f'* kwarg "{key}" not found\n'
            elif value != kwargs2[key]:
                reason += f'* argument "{key}" changed {warn} \n'
                reason += f"  - old: {describe_value(value)} \n"
                reason += f"  - new: {describe_value(kwargs2[key])} \n"

        # TODO: different lengths

        return False, reason
    else:
        return True, None


class IntervalTimer:
    def __init__(self):
        import time

        self.c0 = time.process_time()
        self.t0 = time.time()
        self.stopped = False

    def stop(self):
        self.stopped = True
        import time

        self.c1 = time.process_time()
        self.t1 = time.time()

    def get_walltime_used(self):
        if not self.stopped:
            raise ValueError("not stopped")
        return self.t1 - self.t0

    def get_cputime_used(self):
        if not self.stopped:
            raise ValueError("not stopped")
        return self.c1 - self.c0

    def walltime_interval(self):
        if not self.stopped:
            raise ValueError("not stopped")
        return self.t0, self.t1

    def __str__(self):
        tms = int((self.t1 - self.t0) * 1000)
        cms = int((self.c1 - self.c0) * 1000)
        return f"Timer(wall {tms} ms cpu {cms} ms)"


StateCode = NewType("StateCode", int)


class Cache:
    # TODO: add blocked

    NOT_STARTED = StateCode(0)
    PROCESSING = StateCode(1)
    FAILED = StateCode(3)
    BLOCKED = StateCode(5)
    DONE = StateCode(4)

    TIMESTAMP_TO_REMAKE = 0.0

    allowed_states: List[StateCode] = [NOT_STARTED, FAILED, DONE, BLOCKED, PROCESSING]

    state2desc: Dict[StateCode, str] = {
        NOT_STARTED: "todo",
        BLOCKED: "blocked",
        FAILED: "failed",
        DONE: "done",
        PROCESSING: "processing",
    }

    stateupdate2color = {
        # (state, uptodate)
        (NOT_STARTED, False): {},
        #     (Cache.NOT_STARTED, False): {'color': 'white', 'attrs': ['concealed']},
        (FAILED, False): {"color": "red"},
        (BLOCKED, True): {"color": "brown"},
        (BLOCKED, False): {"color": "brown"},  # XXX
        (DONE, True): {"color": "green"},
        (DONE, False): {"color": "magenta"},
    }

    state2color = {
        NOT_STARTED: {"color": "yellow"},  # {'attrs': ['dark']},
        #     Cache.IN_PROGRESS: {'color': 'yellow'},
        BLOCKED: {"color": "brown"},
        FAILED: {"color": "red"},
        DONE: {"color": "green"},
    }

    styles = {
        NOT_STARTED: dict(color="yellow"),
        DONE: dict(color="green"),
        PROCESSING: dict(color="blue"),
        FAILED: dict(color="red"),
        BLOCKED: dict(color="brown"),
        "ready": dict(color="yellow"),
    }

    glyphs = {
        NOT_STARTED: "?",
        DONE: "✔",
        PROCESSING: "⚙",
        FAILED: "✗",
        BLOCKED: "⯃",
        "ready": "⛦",
        "todo": "⌖",
    }

    state: StateCode
    timestamp_started: Optional[float]
    """ time start """
    timestamp: float
    """ time end """

    int_load_results: Optional[IntervalTimer]
    int_make: Optional[IntervalTimer]
    int_compute: Optional[IntervalTimer]
    int_save_results: Optional[IntervalTimer]
    int_gc: Optional[IntervalTimer]
    jobs_defined: Set[CMJobID]
    hashes_dependencies: Dict[str, object]
    exception: Optional[str]
    backtrace: Optional[str]
    captured_stdout: Optional[str]
    captured_stderr: Optional[str]
    walltime_used: Optional[float]
    cputime_used: Optional[float]

    def __init__(self, state: StateCode):
        assert state in Cache.allowed_states
        self.state = state
        # time start
        self.timestamp_started = None
        # time end
        self.timestamp = 0.0

        # Hash for dependencies when this was computed
        self.hashes_dependencies = {}

        self.jobs_defined = set()

        # in case of failure
        self.exception = None  # a short string
        self.backtrace = None  # a long string
        self.captured_stdout = None
        self.captured_stderr = None

        # total
        self.cputime_used = None
        self.walltime_used = None

        # phases
        # make = load + compute + save

        self.int_make = None
        self.int_load_results = None
        self.int_compute = None
        self.int_save_results = None
        self.int_gc = None

    def __repr__(self):
        return "Cache(%s;%s;cpu:%s;wall:%s)" % (
            Cache.state2desc[self.state],
            self.timestamp,
            self.cputime_used,
            self.walltime_used,
        )


def cache_has_large_overhead(cache: Cache) -> bool:
    overhead = (
        cache.int_load_results.get_walltime_used()
        + cache.int_save_results.get_walltime_used()
        + cache.int_gc.get_walltime_used()
    )
    return overhead - cache.int_make.get_walltime_used() > 1.0


def timing_summary(cache: Cache) -> str:
    dc = duration_compact
    s = "%7s (L %s C %s GC %s S %s)" % (
        dc(cache.int_make.get_walltime_used()),
        dc(cache.int_load_results.get_walltime_used()),
        dc(cache.int_compute.get_walltime_used()),
        dc(cache.int_gc.get_walltime_used()),
        dc(cache.int_save_results.get_walltime_used()),
    )
    return s


class ProgressStage:
    def __init__(self, name: str, iterations: Tuple[Union[float, int], Union[float, int]], iteration_desc):
        self.name = name
        self.iterations = iterations
        self.iteration_desc = iteration_desc
        # We keep track of when to send the event
        self.last_broadcast = None

    def __str__(self):
        return f"[{self.name} {self.iterations} {self.iteration_desc}]"

    def was_finished(self):
        # allow off-by-one conventions
        if isinstance(self.iterations[1], int):
            return self.iterations[0] >= self.iterations[1] - 1
        else:
            return self.iterations[0] >= self.iterations[1]
