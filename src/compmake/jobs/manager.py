from . import (compute_priorities, dependencies_up_to_date, list_todo_targets,
    mark_as_blocked, parents, direct_parents)
from ..events import publish
from ..structures import JobFailed, JobInterrupted, HostFailed
from ..ui import error
from abc import ABCMeta, abstractmethod
from multiprocessing import TimeoutError
import time
from compmake.jobs.queries import direct_children


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
        self.blocked = set()
        self.processing = set()

        self.more = set()
        self.ready_todo = set()

        # contains job_id -> priority
        # computed by precompute_priorities() called by process()
        self.priorities = {}

        # this hash contains  job_id -> async result
        self.processing2result = {}

        self.check_invariants()
        
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


    def next_job(self):
        self.check_invariants()
        
        ''' Returns one job from the ready_todo list 
            (and removes it from there). Uses self.priorities
            to decide which job to use. '''
        ordered = sorted(self.ready_todo,
                         key=lambda job: self.priorities[job])
        best = ordered[-1]
        self.ready_todo.remove(best)
        
        self.check_invariants()
        return best

    def add_targets(self, targets, more=False):
        self.check_invariants()
        
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

        self.check_invariants()

    def instance_some_jobs(self):
        ''' Instances some of the jobs. Uses the
            functions can_accept_job(), next_job(), and ... '''
        # add jobs up to saturations
        self.check_invariants()
        
        while self.ready_todo and self.can_accept_job():
            # todo: add task priority
            job_id = self.next_job()
            self.start_job(job_id)
            #info('Job %s instantiated (more=%s)' % (job_id, make_more))

        self.check_invariants()
        
    def start_job(self, job_id):
        self.check_invariants()
        
        assert job_id in self.todo 
        assert not job_id in self.ready_todo
        assert not job_id in self.processing2result
        assert dependencies_up_to_date(job_id)
        if job_id in self.processing:
            msg = "Something's wrong, the job %r should no be in processing." % job_id
            msg += '\n' + self._get_situation_string()
            assert False, msg

        publish('manager-job-starting', job_id=job_id)
        self.processing.add(job_id)
        make_more = job_id in self.more

        # This is for the simple case of local processing, where
        # the next line actually does something now
        self.publish_progress()

        self.processing2result[job_id] = \
            self.instance_job(job_id, make_more)
            
        self.check_invariants()
        

    def check_job_finished(self, job_id):
        ''' 
            Checks that the job finished succesfully or unsuccesfully. 
            
            Returns True if that's the case.
            Captures HostFailed, JobFailed and returns True.
            
            Returns False if the job is still processing.
            
            Capture KeyboardInterrupt and raises JobInterrupted.
            
            Handles update of various sets. '''
        self.check_invariants()

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
        except HostFailed as e:
            # the execution has been interrupted, but not failed
            self.host_failed(job_id, str(e))
            return True
        except KeyboardInterrupt:
            # self.job_failed(job_id) # not sure
            # No, don't mark as failed 
            # (even though knowing where it was interrupted was good)
            raise JobInterrupted('Keyboard interrupt')

    def host_failed(self, job_id, reason):
        self.check_invariants()
        
        publish('manager-host-failed', job_id=job_id, reason=reason)
        self.processing.remove(job_id)
        del self.processing2result[job_id]
        assert job_id in self.todo
        self.ready_todo.add(job_id)

        self.publish_progress()
        
        self.check_invariants()

    def job_failed(self, job_id):
        ''' The specified job has failed. Update the structures,
            mark any parent as failed as well. '''
        self.check_invariants()
        
        publish('manager-job-failed', job_id=job_id)

        self.failed.add(job_id)
        self.todo.remove(job_id) # XXX
        self.processing.remove(job_id)
        del self.processing2result[job_id]

        its_parents = set(parents(job_id))
        for p in its_parents:
            mark_as_blocked(p, job_id)
            if p in self.todo:
                self.todo.remove(p)
                self.blocked.add(p)
                if p in self.ready_todo:
                    self.ready_todo.remove(p)

        self.publish_progress()
        self.check_invariants()

    def job_succeeded(self, job_id):
        ''' Mark the specified job as succeeded. Update the structures,
            mark any parents which are ready as ready_todo. '''
        self.check_invariants()
        publish('manager-job-succeeded', job_id=job_id)
        del self.processing2result[job_id]
        self.done.add(job_id)
        self.todo.remove(job_id)
        self.processing.remove(job_id)

        parent_jobs = set(direct_parents(job_id))
        for opportunity in self.todo & parent_jobs:
            assert opportunity not in self.processing
            
            for child in direct_children(opportunity):
                # If child is part of all_targets, check that it is done
                # otherwise check that it is done by the DB.
                # Actually -- all children were put in all_targets
                # so we just j
                if not child in self.done:
                    # still some dependency left
                    break
            else:
                self.ready_todo.add(opportunity)
            # this was a bug
            #if dependencies_up_to_date(opportunity):
            #    self.ready_todo.add(opportunity)

        self.check_invariants()
        self.publish_progress()

    def event_check(self):
        pass

    def loop_until_something_finishes(self):
        self.check_invariants()

        # TODO: this should be loop_a_bit_and_then_let's try to instantiate
        # jobs in the ready queue
        for _ in range(10): # XXX
            received = False

            # We make a copy because processing is updated during the loop
            for job_id in self.processing.copy():
                received = received or self.check_job_finished(job_id)
                self.check_invariants()

            if received:
                break
            else:
                publish('manager-loop', processing=list(self.processing))
                time.sleep(0.01) # TODO: make param

            # Process events
            self.event_check()
            self.check_invariants()


    def process(self):
        ''' Start processing jobs. '''
        self.check_invariants()

        if not self.todo:
            # info('Nothing to do.')
            publish('manager-succeeded',
                targets=self.targets, done=self.done,
                all_targets=self.all_targets,
                todo=self.todo, failed=self.failed,
                ready=self.ready_todo,
                processing=self.processing)

            return True

        # precompute job priorities
        publish('manager-phase', phase='compute_priorities')
        self.priorities = compute_priorities(self.all_targets)

        publish('manager-phase', phase='init')
        self.process_init()

        publish('manager-phase', phase='loop')
        try:
            while self.todo:
                self.check_invariants()

                assert self.ready_todo or self.processing
                assert not self.failed.intersection(self.todo)

                self.publish_progress()
                self.instance_some_jobs()
                #self.publish_progress()

                if self.ready_todo and not self.processing:
                    # We time out as there are no resources
                    publish('manager-phase', phase='wait')
                    pass
                    # TODO: make child raise exception if there are no
                    # resources
#                    publish('manager-waits')
#                    publish('manager-failed', reason='No resources.',
#                        targets=self.targets, done=self.done,
#                        todo=self.todo, failed=self.failed,
#                        ready=self.ready_todo,
#                        processing=self.processing,
#                        all_targets=self.all_targets)
#
#                    msg = 'Cannot find computing resources, giving up.'
#                    raise CompmakeException(msg)

                #self.publish_progress()

                self.loop_until_something_finishes()
                self.check_invariants()


            self.publish_progress()

            self.process_finished()

            publish('manager-succeeded',
                targets=self.targets, done=self.done,
                all_targets=self.all_targets,
                todo=self.todo, failed=self.failed, ready=self.ready_todo,
                processing=self.processing)

            return True

        except JobInterrupted as e:
            error('Received JobInterrupted: %s' % e)
            raise
        except KeyboardInterrupt as e:
            ### Interrupt caught by manager outside of get()
            # for example in sleep()
#            error('Received KeyboardInterrupt at: %s' %
#                  traceback.format_exc(e))
            raise
        finally:
            self.cleanup()

    def publish_progress(self):
        publish('manager-progress',
                targets=self.targets,
                done=self.done,
                all_targets=self.all_targets,
                todo=self.todo,
                blocked=self.blocked,
                failed=self.failed,
                ready=self.ready_todo,
                processing=self.processing)
        
    def _get_situation_string(self):
        """ Returns a string summarizing the current situation """
        lists = dict(done=self.done,
                   all_targets=self.all_targets,
                   todo=self.todo,
                    blocked=self.blocked,
                    failed=self.failed,
                    ready=self.ready_todo,
                    processing=self.processing)
        s = ""
        for t, jobs in lists.items():
            jobs = lists[t]
            s += '- %12s: %d %s\n' % (t, len(jobs), jobs)
        return s
    
    def check_invariants(self):
        lists = dict(done=self.done,
                     all_targets=self.all_targets,
                     todo=self.todo,
                     blocked=self.blocked,
                     failed=self.failed,
                     ready=self.ready_todo,
                     processing=self.processing)
        
        def empty_intersection(a, b):
            inter = lists[a] & lists[b]
            if inter:
                msg = 'There should be empty interesection in %r and %r' % (a, b)
                msg += ' but found %s' % inter
                msg += '\n' + self._get_situation_string()
                assert False, msg
        
        empty_intersection('ready', 'processing')
        
        
        
