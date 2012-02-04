from . import (dependencies_up_to_date, list_todo_targets,
    mark_as_blocked, parents, direct_parents)
from ..events import publish
from ..structures import (CompmakeException, JobFailed, JobInterrupted,
    HostFailed)
from ..utils import error, info
from abc import ABCMeta, abstractmethod
from multiprocessing import TimeoutError
import time
from  . import compute_priorities
from compmake.utils.visualization import debug


class AsyncResultInterface:
    # XXX: add abstract method
    def ready(self):
        pass

    def get(self, timeout=0):
        ''' Either:
            - returns normally (value ignored)
            - raises JobFailed
            - raises TimeoutError (not ready)
        '''
        pass


class Manager:

    __metaclass__ = ABCMeta

    def __init__(self):
        # top-level targets
        self.targets = set()
        # targets + dependencies
        self.all_targets = set()
        self.todo = set()
        self.done = set()
        self.failed = set()
        self.processing = set()

        self.more = set()
        self.ready_todo = set()

        # contains job_id -> priority
        # computed by precompute_priorities() called by process()
        self.priorities = {}

        # this hash contains  job_id -> async result
        self.processing2result = {}

### Derived class interface 
    def process_init(self):
        ''' Called before processing '''

    def process_finished(self):
        ''' Called after successful processing (before cleanup) '''

    @abstractmethod
    def can_accept_job(self):
        ''' Return true if a new job can be accepted right away'''

    @abstractmethod
    def instance_job(self, job_id, more):
        ''' Instances a job. '''

    def cleanup(self):
        ''' free up any resource '''
        pass

### 

    def next_job(self):
        ''' Returns one job from the ready_todo list 
            (and removes it from there). Uses self.priorities
            to decide which job to use. '''
        ordered = sorted(self.ready_todo, key=lambda job: self.priorities[job])
        best = ordered[-1]
        self.ready_todo.remove(best)
        return best

    def add_targets(self, targets, more=False):
        # self.targets contains all the top-level targets we were passed
        self.targets.update(targets)

        targets_todo_plus_deps, targets_done = list_todo_targets(targets)

        # both done and todo jobs are added to self.all_targets
        self.all_targets.update(targets_todo_plus_deps)
        self.all_targets.update(targets_done)
        # however, we will only do the ones needed 
        self.todo.update(targets_todo_plus_deps)
        self.done.update(targets_done)

        if more:
            self.more.update(targets)
            self.todo.update(targets)

        self.ready_todo = set([job_id for job_id in self.todo
                      if dependencies_up_to_date(job_id)])

    def instance_some_jobs(self):
        ''' Instances some of the jobs. Uses the
            functions can_accept_job(), next_job(), and ... '''
        # add jobs up to saturations
        while self.ready_todo and self.can_accept_job():
            # todo: add task priority
            job_id = self.next_job()
            assert job_id in self.todo and not job_id in self.ready_todo
            assert dependencies_up_to_date(job_id)

            self.processing.add(job_id)
            make_more = job_id in self.more

            self.processing2result[job_id] = \
                self.instance_job(job_id, make_more)

            # info('Job %s instantiated (more=%s)' % (job_id, make_more))

    def check_job_finished(self, job_id):
        ''' Checks that the job finished. Returns true if that's the case.
            Handles update of various sets '''
        assert job_id in self.processing
        assert job_id in self.todo
        assert not job_id in self.ready_todo

        async_result = self.processing2result[job_id]

        try:
            if async_result.ready():
                async_result.get()
                self.job_succeeded(job_id)
                return True
        except TimeoutError:
            # Result not ready yet
            return False
        except JobFailed:
            self.job_failed(job_id)
            return True
        except HostFailed:
            # the execution has been interrupted, but not failed
            self.host_failed(job_id)
            return True
        except KeyboardInterrupt:
            raise JobInterrupted('Keyboard interrupt')

    def host_failed(self, job_id):
        error('Job %s: host failed' % job_id)
        self.processing.remove(job_id)
        del self.processing2result[job_id]
        assert job_id in self.todo
        self.ready_todo.add(job_id)

    def job_failed(self, job_id):
        ''' The specified job has failed. Update the structures,
            mark any parent as failed as well. '''
        #error('Job %s failed ' % job_id)
        self.failed.add(job_id)
        self.todo.remove(job_id)
        self.processing.remove(job_id)
        del self.processing2result[job_id]

        its_parents = set(parents(job_id))
        for p in its_parents:
            mark_as_blocked(p, job_id)
            if p in self.todo:
                self.todo.remove(p)
                self.failed.add(p)
                if p in self.ready_todo:
                    self.ready_todo.remove(p)

    def job_succeeded(self, job_id):
        #info('Job %s succeded ' % job_id)
        ''' The specified job as succeeded. Update the structures,
            mark any parents which are ready as ready_todo. '''
        del self.processing2result[job_id]
        self.done.add(job_id)
        self.todo.remove(job_id)
        self.processing.remove(job_id)

        parent_jobs = direct_parents(job_id)
        for opportunity in self.todo.intersection(set(parent_jobs)):
            if dependencies_up_to_date(opportunity):
                self.ready_todo.add(opportunity)

    def event_check(self):
        pass

    def loop_until_something_finishes(self):
        while True:
            received = False

            # We make a copy because processing is updated during the loop
            for job_id in self.processing.copy():
                received = received or self.check_job_finished(job_id)

            if received:
                break
            else:
                time.sleep(0.05)

            # Process events
            self.event_check()

    def process(self):
        ''' Start processing jobs. '''

        # precompute job priorities
        debug('Computing priorities...')
        self.priorities = compute_priorities(self.all_targets)

        if not self.todo:
            info('Nothing to do.')
            return True

        debug('Initiating process...')
        self.process_init()

        debug('Starting make loop...')
        try:
            while self.todo:
                assert self.ready_todo or self.processing
                assert not self.failed.intersection(self.todo)

                self.publish_progress()
                self.instance_some_jobs()
                self.publish_progress()
                if self.ready_todo and not self.processing:
                    publish('manager-failed', reason='No resources.',
                        targets=self.targets, done=self.done,
                        todo=self.todo, failed=self.failed,
                        ready=self.ready_todo,
                        processing=self.processing,
                        all_targets=self.all_targets)

                    msg = 'Cannot find computing resources, giving up.'
                    raise CompmakeException(msg)

                self.publish_progress()

                self.loop_until_something_finishes()


            self.process_finished()

            publish('manager-succeeded',
                targets=self.targets, done=self.done, all_targets=self.all_targets,
                todo=self.todo, failed=self.failed, ready=self.ready_todo,
                processing=self.processing)

            return True

        except JobInterrupted as e:
            # XXX I'm getting confused
            error('Received JobInterrupted: %s' % e)
            raise
        except KeyboardInterrupt: ### tmp - just understanding who raiss this
            #error('Received KeyboardInterrupt at: %s' %
            #      traceback.format_exc(e))
            raise
        finally:
            self.cleanup()


    def publish_progress(self):
        publish('manager-progress', targets=self.targets, done=self.done,
                all_targets=self.all_targets, todo=self.todo,
                failed=self.failed, ready=self.ready_todo,
                processing=self.processing)
