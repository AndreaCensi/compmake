# -*- coding: utf-8 -*-
from abc import ABCMeta, abstractmethod
from multiprocessing import TimeoutError
import itertools
import os
import shutil
import time
import traceback
import warnings

from compmake.constants import CompmakeConstants
from compmake.jobs.storage import db_job_add_dynamic_children, db_job_add_parent
from compmake.state import get_compmake_config
from contracts import ContractsMeta, contract, indent

from ..events import publish
from ..exceptions import CompmakeBug, HostFailed, JobFailed, JobInterrupted
from ..jobs import (assert_job_exists, get_job_cache, job_cache_exists,
    job_exists, job_userobject_exists)
from ..jobs.actions_newprocess import result_dict_check
from ..structures import Cache
from ..utils import make_sure_dir_exists
from .actions import mark_as_blocked
from .priority import compute_priorities
from .queries import direct_children, direct_parents
from .uptodate import CacheQueryDB

__all__ = [
    'Manager',
    'AsyncResultInterface',
]


class AsyncResultInterface(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def ready(self):
        """ Returns True if it is ready (completed or failed). """

    @abstractmethod
    def get(self, timeout=0):
        """ Either:
            - returns a dictionary with fields:
                new_jobs: list of jobs created
                user_object_deps: ...
            or:
            - raises JobFailed
            - raises HostFailed
            - raises JobInterrupted
            - raises TimeoutError (not ready)
        """


class ManagerLog(object):
    __metaclass__ = ContractsMeta

    def __init__(self, db):
        storage = os.path.abspath(db.basepath)
        logdir = os.path.join(storage, 'logs')
        if os.path.exists(logdir):
            shutil.rmtree(logdir)
        log = os.path.join(logdir, 'manager.log')
        make_sure_dir_exists(log)
        self.f = open(log, 'w')

    def log(self, s, **kwargs):
        for k, v in kwargs.items():
            s += '\n - %15s: %s' % (k, v)
        self.f.write(s)
        # print(s)
        self.f.write('\n')

        self.f.flush()


class Manager(ManagerLog):

    @contract(recurse='bool')
    def __init__(self, context, cq, recurse=False):  # @UnusedVariable
        self.context = context
        # self.cq = cq
        self.db = context.get_compmake_db()
        ManagerLog.__init__(self, db=self.db)

        self.recurse = recurse

        # top-level targets added by users
        self.targets = set()

        # top-level targets + all their dependencies
        self.all_targets = set()
        # some jobs might be deleted, they go here
        self.deleted = set()

        # all_targets - targets_delted = sum of rest:

        # a job is in exactly one of these states
        self.todo = set()
        # |
        # V
        self.ready_todo = set()
        # |
        # V
        # processing and processing2result have the same keys
        # (it's redundant)
        self.processing = set()
        # this hash contains  job_id -> async result
        self.processing2result = {}
        # |
        # V
        # final states
        self.done = set()
        self.failed = set()
        self.blocked = set()

        # contains job_id -> priority
        # computed by ``precompute_priorities()`` called by process()
        self.priorities = {}

        self.check_invariants()

    # ## Derived class interface
    def process_init(self):
        """ Called before processing """

    def process_finished(self):
        """ Called after successful processing (before cleanup) """

    @abstractmethod
    def can_accept_job(self, reasons):
        """ Return true if a new job can be accepted right away"""

    @abstractmethod
    def instance_job(self, job_id):
        """ Instances a job. """

    def cleanup(self):
        """ free up any resource, called wheter succesfull or not."""
        pass

    @contract(returns='str')
    def next_job(self):
        """
            Returns one job from the ready_todo list
            Uses self.priorities to decide which job to use.
        """
        self.check_invariants()

        ordered = sorted(self.ready_todo,
                         key=lambda job: self.priorities[job])
        best = ordered[-1]

        # print('choosing %s job %r' % (self.priorities[best], best))
        return best

    def add_targets(self, targets):
        self.log('add_targets()', targets=targets)
        self.check_invariants()
        for t in targets:
            assert_job_exists(t, self.db)

            if t in self.processing:
                msg = 'Adding a job already in processing: %r' % t
                raise CompmakeBug(msg)

            if t in self.targets:
                if t in self.ready_todo:
                    self.ready_todo.remove(t)
                if t in self.todo:
                    self.todo.remove(t)
                if t in self.all_targets:
                    self.all_targets.remove(t)
                if t in self.done:
                    self.done.remove(t)

        # self.targets contains all the top-level targets we were passed
        self.targets.update(targets)

        # logger.info('Checking dependencies...')
        cq = CacheQueryDB(self.db)
        # Note this would not work for recursive jobs
        # cq = self.cq
        targets_todo_plus_deps, targets_done, ready_todo = \
            cq.list_todo_targets(
                targets)
        not_ready = targets_todo_plus_deps - ready_todo

        self.log('computed todo',
                 targets_todo_plus_deps=targets_todo_plus_deps,
                 targets_done=targets_done,
                 ready_todo=ready_todo,
                 not_ready=not_ready)

        self.log('targets_todo_plus_deps: %s' % targets_todo_plus_deps)

        # print(' targets_todo_plus_deps: %s ' % targets_todo_plus_deps)
        # print('           targets_done: %s ' % targets_done)
        # print('             ready_todo: %s ' % ready_todo)
        # both done and todo jobs are added to self.all_targets

        # let's check the additional jobs exist
        for d in targets_todo_plus_deps - set(targets):
            if not job_exists(d, self.db):
                msg = 'Adding job that does not exist: %r.' % d
                raise CompmakeBug(msg)

        self.all_targets.update(targets_todo_plus_deps)
        self.all_targets.update(targets_done)

        # ok, careful here, there might be jobs that are
        # already in processing

        # XXX: we should clean the Cache of a job before making it
        self.done.update(targets_done - self.processing)

        todo_add = not_ready - self.processing
        self.todo.update(not_ready - self.processing)
        self.log('add_targets():adding to todo', todo_add=todo_add, todo=self.todo)
        ready_add = ready_todo - self.processing
        self.log('add_targets():adding to ready', ready=self.ready_todo, ready_add=ready_add)
        self.ready_todo.update(ready_add)
        # this is a quick fix but I'm sure more thought is to be given
        for a in ready_add:
            if a in self.todo:
                self.todo.remove(a)
        for a in todo_add:
            if a in self.ready_todo:
                self.ready_todo.remove(a)

        needs_priorities = self.todo | self.ready_todo
        misses_priorities = needs_priorities - set(self.priorities)
        new_priorities = compute_priorities(misses_priorities, cq=cq,
                                            priorities=self.priorities)
        self.priorities.update(new_priorities)

        self.check_invariants()

        self.log('after add_targets()',
                 processing=self.processing,
                 ready_todo=self.ready_todo,
                 todo=self.todo,
                 done=self.done)

    def instance_some_jobs(self):
        """
            Instances some of the jobs. Uses the
            functions can_accept_job(), next_job(), and ...

            Returns a dictionary of wait conditions.
        """
        self.check_invariants()

        n = 0
        reasons = {}
        while True:
            if not self.ready_todo:
                reasons['jobs'] = 'no jobs ready'
                break

            if not self.can_accept_job(reasons):
                break

            # todo: add task priority
            job_id = self.next_job()
            assert job_id in self.ready_todo

            self.log('chosen next_job', job_id=job_id)

            self.start_job(job_id)
            n += 1

#         print('cur %d Instanced %d, %s' % (len(self.processing2result), n, reasons))

        self.check_invariants()
        return reasons

    def _raise_bug(self, func, job_id):
        msg = "%s: Assumptions violated with job %r." % (func, job_id)
        # msg += '\n' + self._get_situation_string()

        sets = [
            ('done', self.done),
            ('all_targets', self.all_targets),
            ('todo', self.todo),
            ('blocked', self.blocked),
            ('failed', self.failed),
            ('ready', self.ready_todo),
            ('processing', self.processing),
            ('proc2result', self.processing2result),
        ]

        for name, cont in sets:
            contained = job_id in cont
            msg += '\n in %15s? %s' % (name, contained)

        raise CompmakeBug(msg)

    def start_job(self, job_id):
        self.log('start_job', job_id=job_id)
        self.check_invariants()
        if not job_id in self.ready_todo:
            self._raise_bug('start_job', job_id)

        publish(self.context, 'manager-job-starting', job_id=job_id)
        self.ready_todo.remove(job_id)
        self.processing.add(job_id)
        self.processing2result[job_id] = self.instance_job(job_id)

        # This is for the simple case of local processing, where
        # the next line actually does something now
        self.publish_progress()

        self.check_invariants()

    def check_job_finished(self, job_id, assume_ready=False):
        '''
            Checks that the job finished succesfully or unsuccesfully.

            Returns True if that's the case.
            Captures HostFailed, JobFailed and returns True.

            Returns False if the job is still processing.

            Capture KeyboardInterrupt and raises JobInterrupted.

            Handles update of various sets.
        '''
        self.log('check_job_finished', job_id=job_id)
        self.check_invariants()

        def bug():
            self._raise_bug('check_job_finished', job_id)

        if not job_id in self.processing:
            bug()

        async_result = self.processing2result[job_id]

        try:
            if not assume_ready and not async_result.ready():
                return False

            if assume_ready:
                timeout = 10
            else:
                timeout = 0

            result = async_result.get(timeout=timeout)
            result_dict_check(result)

            check_job_cache_state(job_id, states=[Cache.DONE], db=self.db)

            self.job_succeeded(job_id)
            self.check_invariants()

            self.check_job_finished_handle_result(job_id, result)
            self.check_invariants()
            # this will schedule the parents, so let's do it later

            self.check_invariants()

            return True

        except TimeoutError:
            if assume_ready:
                msg = 'Got Timeout while assume_ready for %r' % job_id
                raise CompmakeBug(msg)
            # Result not ready yet
            return False
        except JobFailed as e:
            # it is the responsibility of the executer to mark_job_as_failed,
            # so we can check that
            check_job_cache_state(job_id, states=[Cache.FAILED], db=self.db)
            self.job_failed(job_id, deleted_jobs=e.deleted_jobs)

            publish(self.context, 'job-failed', job_id=job_id,
                    host="XXX", reason=e.reason, bt=e.bt)
            return True
        except HostFailed as e:
            # the execution has been interrupted, but not failed
            self.host_failed(job_id)
            publish(self.context, 'manager-host-failed', host=e.host,
                    job_id=job_id, reason=e.reason, bt=e.bt)
            return True
        except KeyboardInterrupt as e:
            # self.job_failed(job_id) # not sure
            # No, don't mark as failed
            # (even though knowing where it was interrupted was good)
            # XXX
            print(traceback.format_exc())
            raise JobInterrupted('Keyboard interrupt')

    def job_is_deleted(self, job_id):
        if job_exists(job_id, self.db):
            msg = 'Job %r declared deleted still exists' % job_id
            raise CompmakeBug(msg)
        if job_id in self.all_targets:
            if job_id in self.todo:
                self.todo.remove(job_id)
            if job_id in self.ready_todo:
                self.ready_todo.remove(job_id)
            self.deleted.add(job_id)

    def check_job_finished_handle_result(self, job_id, result):
        # print('result of %r: %s' % (job_id, result))
        self.check_invariants()
        self.log('check_job_finished_handle_result', job_id=job_id,
                 new_jobs=result['new_jobs'],
                 user_object_deps=result['user_object_deps'],
                 deleted_jobs=result['deleted_jobs'])

        new_jobs = result['new_jobs']
        deleted_jobs = result['deleted_jobs']
        #print('deleted jobs: %r' % deleted_jobs)
        map(self.job_is_deleted, deleted_jobs)
        # print('Job %r generated %r' % (job_id, new_jobs))

        # Update the child->parent relation
        # self._update_parents_relation(new_jobs)

        # Job succeeded? we can check in the DB
        check_job_cache_state(job_id=job_id, db=self.db,
                                  states=[Cache.DONE])

        # print('job %r succeeded' % job_id)
        self.check_invariants()

        # Check if the result of this job contains references
        # to other jobs
        deps = result['user_object_deps']
        if deps:
            # print('Job %r results contain references to jobs: %s'
            # % (job_id, deps))

            # We first add extra dependencies to all those jobs
            jobs_depending_on_this = direct_parents(job_id, self.db)
            # print('need to update %s' % jobs_depending_on_this)
            for parent in jobs_depending_on_this:
                db_job_add_dynamic_children(job_id=parent, children=deps,
                                            returned_by=job_id, db=self.db)

                # also add inverse relation
                for d in deps:
                    self.log('updating dep', job_id=job_id, parent=parent, d=d)
                    db_job_add_parent(job_id=d, parent=parent, db=self.db)

            for parent in jobs_depending_on_this:
                self.log('rescheduling parent',
                         job_id=job_id,
                         parent=parent)
                # print(' its parent %r' % parent)
                if parent in self.all_targets:
                    # print('was also in targets')
                    # Remove it from the "ready_todo_list"
                    if parent in self.processing2result:
                        msg = ('parent %s of %s is already processing?' %
                               (job_id, parent))
                        raise CompmakeBug(msg)

                    if parent in self.done:
                        msg = (' parent %s of %s is already done?' %
                               (job_id, parent))
                        warnings.warn('not sure of this...')
                        # raise CompmakeBug(msg)#

                    self.all_targets.remove(parent)
                    if parent in self.failed:
                        self.failed.remove(parent)
                    if parent in self.blocked:
                        self.blocked.remove(parent)
                    if parent in self.done:
                        self.done.remove(parent)
                    if parent in self.ready_todo:
                        self.ready_todo.remove(parent)
                    if parent in self.todo:
                        self.todo.remove(parent)
                    self.check_invariants()

                    self.add_targets([parent])
                    self.check_invariants()

        if self.recurse:
            # print('adding targets %s' % new_jobs)
            cocher = set()
            for j in new_jobs:
                if j in self.all_targets:
                    # msg = ('Warning, job %r generated %r which was '
                    # 'already a target. I will not re-add it to the
                    # queue. '
                    # % (job_id, j))
                    # print(msg)
                    pass
                else:
                    cocher.add(j)
            if cocher:
                self.add_targets(cocher)

        self.check_invariants()

    def host_failed(self, job_id):
        self.log('host_failed', job_id=job_id)
        self.check_invariants()

        #from compmake.ui.visualization import error
        #error('Host failed, rescheduling job %r.' % job_id)
        self.processing.remove(job_id)
        del self.processing2result[job_id]
        # rescheduling
        self.ready_todo.add(job_id)

        self.publish_progress()

        self.check_invariants()

    def job_failed(self, job_id, deleted_jobs):
        """ The specified job has failed. Update the structures,
            mark any parent as failed as well. """
        self.log('job_failed', job_id=job_id)
        self.check_invariants()
        assert job_id in self.processing

        map(self.job_is_deleted, deleted_jobs)

        self.failed.add(job_id)
        self.processing.remove(job_id)
        del self.processing2result[job_id]

        self.check_invariants()

        publish(self.context, 'manager-job-failed', job_id=job_id)

        # TODO: more efficient query
        #parent_jobs = set(parents(job_id, db=self.db))
        from compmake.jobs.uptodate import direct_uptodate_deps_inverse_closure
        parent_jobs = direct_uptodate_deps_inverse_closure(job_id, db=self.db)

        parents_todo = set(self.todo & parent_jobs)
        for p in parents_todo:
            mark_as_blocked(p, job_id, db=self.db)
            self.todo.remove(p)
            self.blocked.add(p)

        self.publish_progress()
        self.check_invariants()

    def job_succeeded(self, job_id):
        """ Mark the specified job as succeeded. Update the structures,
            mark any parents which are ready as ready_todo. """
        self.log('job_succeeded', job_id=job_id)
        self.check_invariants()
        publish(self.context, 'manager-job-succeeded', job_id=job_id)
        assert job_id in self.processing

        self.processing.remove(job_id)
        del self.processing2result[job_id]
        self.done.add(job_id)

        # parent_jobs = set(direct_parents(job_id, db=self.db))
        from compmake.jobs.uptodate import direct_uptodate_deps_inverse
        parent_jobs = direct_uptodate_deps_inverse(job_id, db=self.db)
        cq = CacheQueryDB(self.db)

        parents_todo = set(self.todo & parent_jobs)
        self.log('considering parents', parents_todo=parents_todo)
        for opportunity in parents_todo:
            # print('parent %r in todo' % (opportunity))
            if opportunity in self.processing:
                msg = 'Parent %r of %r already processing' % (
                    opportunity, job_id)
                if CompmakeConstants.try_recover:
                    print(msg)
                    continue
                else:
                    raise CompmakeBug(msg)
            assert opportunity not in self.processing

            self.log('considering opportuniny', opportunity=opportunity,
                     job_id=job_id)

            its_children = direct_children(opportunity, db=self.db)
            # print('its children: %r' % its_children)

            for child in its_children:
                # If child is part of all_targets, check that it is done
                # otherwise check that it is done by the DB.
                if child in self.all_targets:
                    if not child in self.done:
                        self.log('parent still waiting another child',
                                 opportunity=opportunity,
                                 child=child)
                        # logger.info('parent %r still waiting on %r' %
                        # (opportunity, child))
                        # still some dependency left
                        break
                else:
                    up, _, _ = cq.up_to_date(child)
                    if not up:
                        # print('The child %s is not up_to_date' % child)
                        break

            else:
                # print('parent %r is now ready' % (opportunity))
                self.log('parent is ready', opportunity=opportunity)
                self.todo.remove(opportunity)
                self.ready_todo.add(opportunity)

        self.check_invariants()
        self.publish_progress()

    def event_check(self):
        pass

    def check_any_finished(self):
        """
            Checks that any of the jobs finished.

            Returns True if something finished (either success or failure).
            Returns False if something finished unseccesfully.
        """
        # We make a copy because processing is updated during the loop
        received = False
        for job_id in self.processing.copy():
            received = received or self.check_job_finished(job_id)
            self.check_invariants()
        return received

    def loop_until_something_finishes(self):
        self.check_invariants()

        manager_wait = get_compmake_config('manager_wait')

        # TODO: this should be loop_a_bit_and_then_let's try to instantiate
        # jobs in the ready queue
        for _ in range(10):  # XXX
            received = self.check_any_finished()

            if received:
                break
            else:
                publish(self.context, 'manager-loop',
                        processing=list(self.processing))
                time.sleep(manager_wait)  # TODO: make param

            # Process events
            self.event_check()
            self.check_invariants()

    def process(self):
        """ Start processing jobs. """
        # logger.info('Started job manager with %d jobs.' % (len(self.todo)))
        self.check_invariants()

        if not self.todo and not self.ready_todo:
            publish(self.context, 'manager-succeeded',
                    nothing_to_do=True,
                    targets=self.targets, done=self.done,
                    all_targets=self.all_targets,
                    todo=self.todo,
                    failed=self.failed,
                    blocked=self.blocked,
                    ready=self.ready_todo,
                    processing=self.processing)
            return True

        publish(self.context, 'manager-phase', phase='init')
        self.process_init()

        publish(self.context, 'manager-phase', phase='loop')
        try:
            while self.todo or self.ready_todo or self.processing:
                self.check_invariants()
                # either something ready to do, or something doing
                # otherwise, we are completely blocked
                if (not self.ready_todo) and (not self.processing):
                    msg = ('Nothing ready to do, and nothing cooking. '
                           'This probably means that the Compmake job '
                           'database was inconsistent. '
                           'This might happen if the job creation is '
                           'interrupted. Use the command "check-consistency" '
                           'to check the database consistency.\n'
                           + self._get_situation_string())
                    raise CompmakeBug(msg)

                self.publish_progress()
                waiting_on = self.instance_some_jobs()
                # self.publish_progress()

                publish(self.context, 'manager-wait', reasons=waiting_on)

                if self.ready_todo and not self.processing:
                    # We time out as there are no resources
                    publish(self.context, 'manager-phase', phase='wait')

                self.loop_until_something_finishes()
                self.check_invariants()

            # end while
            assert not self.todo
            assert not self.ready_todo
            assert not self.processing
            self.check_invariants()

            self.publish_progress()

            self.process_finished()

            publish(self.context, 'manager-succeeded',
                    nothing_to_do=False,
                    targets=self.targets, done=self.done,
                    all_targets=self.all_targets,
                    todo=self.todo, failed=self.failed, ready=self.ready_todo,
                    blocked=self.blocked,
                    processing=self.processing)

            return True

        except JobInterrupted as e:
            from ..ui import error

            error('Received JobInterrupted: %s' % e)
            raise
        except KeyboardInterrupt:
            raise KeyboardInterrupt('Manager interrupted.')
        finally:
            self.cleanup()

    def publish_progress(self):
        publish(self.context, 'manager-progress',
                targets=self.targets,
                done=self.done,
                all_targets=self.all_targets,
                todo=self.todo,
                blocked=self.blocked,
                failed=self.failed,
                ready=self.ready_todo,
                processing=self.processing,
                deleted=self.deleted)

    def _get_situation_string(self):
        """ Returns a string summarizing the current situation """
        lists = dict(done=self.done,
                     all_targets=self.all_targets,
                     todo=self.todo,
                     blocked=self.blocked,
                     failed=self.failed,
                     ready=self.ready_todo,
                     deleted=self.deleted,
                     processing=self.processing)
        s = ""
        for t, jobs in lists.items():
            jobs = lists[t]
            s += '- %12s: %d\n' % (t, len(jobs))

        # if False:
        s += '\n In more details:'
        for t, jobs in lists.items():
            jobs = lists[t]
            if not jobs:
                s += '\n- %12s: -' % (t)
            elif len(jobs) < 20:
                s += '\n- %12s: %d %s' % (t, len(jobs), sorted(jobs))

        return s

    def check_invariants(self):
        if not CompmakeConstants.debug_check_invariants:
            return
        lists = dict(done=self.done,
                     all_targets=self.all_targets,
                     todo=self.todo,
                     blocked=self.blocked,
                     failed=self.failed,
                     ready_todo=self.ready_todo,
                     processing=self.processing,
                     deleted=self.deleted)

        def empty_intersection(a, b):
            inter = lists[a] & lists[b]
            if inter:
                msg = 'There should be empty intersection in %r and %r' % (
                    a, b)
                msg += ' but found %s' % inter

                st = self._get_situation_string()
                if len(st) < 500:
                    msg += '\n' + st

                raise CompmakeBug(msg)

        def partition(sets, result):
            S = set()
            for s in sets:
                S = S | lists[s]

            if S != lists[result]:
                msg = 'These two sets should be the same:\n'
                msg += ' %s = %s\n' % (" + ".join(list(sets)), result)
                msg += ' first = %s\n' % S
                msg += ' second = %s\n' % lists[result]
                msg += ' first-second = %s\n' % (S - lists[result])
                msg += ' second-first = %s\n' % (lists[result] - S)

                st = self._get_situation_string()
                if len(st) < 500:
                    msg += '\n' + st

                raise CompmakeBug(msg)

            for a, b in itertools.product(sets, sets):
                if a == b:
                    continue
                empty_intersection(a, b)

        partition(['done', 'failed', 'blocked',
                   'todo', 'ready_todo', 'processing', 'deleted'],
                  'all_targets')

        if False:

            for job_id in self.done:
                if not job_exists(job_id, self.db):
                    raise CompmakeBug('job %r in done does not exist' % job_id)

            for job_id in self.todo:
                if not job_exists(job_id, self.db):
                    raise CompmakeBug('job %r in todo does not exist' % job_id)

            for job_id in self.failed:
                if not job_exists(job_id, self.db):
                    raise CompmakeBug(
                        'job %r in failed does not exist' % job_id)

            for job_id in self.blocked:
                if not job_exists(job_id, self.db):
                    raise CompmakeBug(
                        'job %r in blocked does not exist' % job_id)


def check_job_cache_state(job_id, states, db):
    """ Raises CompmakeBug if the job is not marked as done. """
    if not CompmakeConstants.extra_checks_job_states:  # XXX: extra check
        return

    if not job_cache_exists(job_id, db):
        msg = ('The job %r was reported as done/failed but no record of '
               'it was found.' % job_id)
        raise CompmakeBug(msg)
    else:
        cache = get_job_cache(job_id, db)
        if not cache.state in states:
            msg = ('Wrong state for %r: %s instead of %r ' %
                   (job_id, Cache.state2desc[cache.state],
                    [Cache.state2desc[s] for s in states]))
            raise CompmakeBug(msg)

        if cache.state == Cache.DONE:
            if not job_userobject_exists(job_id, db):
                msg = 'Job %r marked as DONE but no userobject exists' % job_id
                raise CompmakeBug(msg)

#
# if False:
#     def clean_other_jobs(self, job_id, new_jobs):
#         """ job_id has finished and the jobs in new_jobs have been
#             generated. We should look in the DB if in the past
#             it had generated other jobs and delete them """
#         # print('cleaning other jobs after %r generated %r' % (job_id,
#         # new_jobs))
#         db = self.db
#         extra = []
#         # XXX: slow
#         for g in all_jobs(db=db):
#             if get_job(g, db=db).defined_by[-1] == job_id:
#                 if not g in new_jobs:
#                     extra.append(g)
#
#         for g in extra:
#             if g in self.processing:
#                 print(
#                     'a mess - cannot eliminate job %s because processing' % g)
#             else:
#                 if g in self.targets:
#                     # print('removing job %r which was an explicit target' % g)
#                     self.targets.remove(g)
#                 if g in self.all_targets:
#                     self.all_targets.remove(g)
#                 if g in self.todo:
#                     self.todo.remove(g)
#                 if g in self.ready_todo:
#                     self.ready_todo.remove(g)
#                 if g in self.ready_todo:
#                     self.todo.remove(g)
#                 if g in self.failed:
#                     self.failed.remove(g)
#                 if g in self.blocked:
#                     self.blocked.remove(g)
#
#             # print('Erasing previously generated job %r (%s) removed.' % (
#             # g, job.defined_by))
#             delete_all_job_data(g, db=db)
#
#             # clean dependencies as well
#             self.clean_other_jobs(g, [])


def check_job_cache_says_failed(job_id, db, e):
    """ Raises CompmakeBug if the job is not marked as failed. """
    if not job_cache_exists(job_id, db):
        msg = ('The job %r was reported as failed but no record of '
               'it was found.' % job_id)
        msg += '\n' + 'JobFailed exception:'
        msg += '\n' + indent(str(e), "| ")
        raise CompmakeBug(msg)
    else:
        cache = get_job_cache(job_id, db)
        if not cache.state == Cache.FAILED:
            msg = ('The job %r was reported as failed but it was '
                   'not marked as such in the DB.' % job_id)
            msg += '\n seen state: %s ' % Cache.state2desc[cache.state]
            msg += '\n' + 'JobFailed exception:'
            msg += '\n' + indent(str(e), "| ")
            raise CompmakeBug(msg)

#
#
# def clean_other_jobs_distributed(db, job_id, new_jobs, recurse=False):
# """ job_id has finished and the jobs in new_jobs have been
# generated. We should look in the DB if in the past
# it had generated other jobs and delete them """
# #print('cleaning other jobs after %r generated %r' % (job_id, new_jobs))
#     extra = []
#     # XXX: slow
#     for g in all_jobs(db=db):
#         try:
#             job = get_job(g, db)
#         except:
#             # race condition
#             continue
#
#         if job.defined_by[-1] == job_id:
#             if not g in new_jobs:
#                 extra.append(g)
#
#         delete_all_job_data(g, db=db)
#
#         # clean dependencies as well
#         if recurse:
#             clean_other_jobs_distributed(db, g, [])
