from compmake import CMJobID, Context, Event, register_handler

__all__ = [
    "Tracker",
]

from compmake.registered_events import EVENT_MANAGER_PROGRESS


class Tracker:
    """This class keeps track of the status of the computation.
    It listens to progress events."""

    processing: set[CMJobID]
    targets: set[CMJobID]
    all_targets: set[CMJobID]
    todo: set[CMJobID]
    failed: set[CMJobID]
    ready: set[CMJobID]
    blocked: set[CMJobID]
    done: set[CMJobID]
    done_by_me: set[CMJobID]
    wait_reasons: dict
    status: dict[str, str]

    def __init__(self):
        register_handler("job-progress", self.event_job_progress)
        register_handler("job-progress-plus", self.event_job_progress_plus)
        register_handler(EVENT_MANAGER_PROGRESS, self.event_manager_progress)
        register_handler("manager-loop", self.event_manager_loop)
        register_handler("manager-wait", self.event_manager_wait)

        self.processing = set()
        self.targets = set()
        self.all_targets = set()
        self.todo = set()
        self.failed = set()
        self.ready = set()
        self.blocked = set()
        self.done = set()
        self.done_by_me = set()
        # Status of jobs in "processing" state
        self.status = {}
        self.status_plus = {}
        self.nloops = 0
        self.wait_reasons = {}

    async def event_manager_wait(self, context: Context, event: Event) -> None:
        self.wait_reasons = event.reasons

    async def event_manager_loop(self, context: Context, event: Event) -> None:
        self.nloops += 1

    async def event_job_progress(self, context: Context, event: Event) -> None:
        """Receive news from the job"""
        # attrs = ['job_id', 'host', 'done', 'progress', 'goal']
        stat = f"{event.progress}/{event.goal}"
        self.status[event.job_id] = stat

    async def event_job_progress_plus(self, context: Context, event: Event) -> None:
        self.status_plus[event.job_id] = event.stack
        if len(event.stack) > 0:
            i, n = event.stack[0].iterations
            if isinstance(n, int):
                stat = f"{i + 1}/{n}"
            else:
                perc = i * 100.0 / n
                stat = f"{perc:.1f}%"
        else:
            stat = "-"
        self.status[event.job_id] = stat

    async def event_manager_progress(self, context: Context, event: Event) -> None:
        """Receive progress message (updates processing)"""
        # attrs=['targets', 'done', 'todo', 'failed', 'ready', 'processing', 'done_by_me']
        self.processing = event.processing
        self.targets = event.targets
        self.todo = event.todo
        self.all_targets = event.all_targets
        self.failed = event.failed
        self.ready = event.ready
        self.done = event.done
        self.done_by_me = event.done_by_me
        self.blocked = event.blocked

        # Put unknown for new jobs
        for job_id in self.processing:
            if not job_id in self.status:
                self.status[job_id] = "-"
            if not job_id in self.status:
                self.status_plus[job_id] = "-"

        # Remove completed jobs from status
        for job_id in list(self.status.keys()):
            if not job_id in self.processing:
                del self.status[job_id]

        for job_id in list(self.status_plus.keys()):
            if not job_id in self.processing:
                del self.status_plus[job_id]


# print('Processing is now %r and status is %r %r' %
#              (self.processing, self.status.keys(), self.status_plus.keys()))
