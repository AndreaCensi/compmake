# -*- coding: utf-8 -*-
import os

from .sge_misc import check_sge_environment
from .sge_sub import SGESub
from compmake.jobs.manager import Manager
from compmake.utils import isodate_with_secs
from contracts import contract


__all__ = [
    'SGEManager',
]


class SGEManager(Manager):
    """ Runs compmake jobs using a SGE implementation """

    @contract(num_processes=int, recurse='bool')
    def __init__(self, context, cq, recurse, num_processes):
        Manager.__init__(self, context=context, cq=cq, recurse=recurse)

        self.num_processes = num_processes

        check_sge_environment()

        storage = os.path.abspath(self.db.basepath)
        timestamp = isodate_with_secs().replace(':', '-')
        spool = os.path.join(storage, 'sge', timestamp)
        if not os.path.exists(spool):
            os.makedirs(spool)


        self.sub_available = set()
        self.sub_processing = set()  # available + processing = subs.keys
        self.subs = {}  # name -> sub
        for i in range(self.num_processes):
            name = 'w%02d' % i
            self.subs[name] = SGESub(name, db=self.db, spool=spool)
        self.job2subname = {}
        # all are available
        self.sub_available.update(self.subs)

    def get_resources_status(self):
        resource_available = {}

        assert len(self.sub_processing) == len(self.processing)
        # only one job at a time
        process_limit_ok = len(self.sub_processing) < self.num_processes
        if not process_limit_ok:
            resource_available['nproc'] = (False,
                                           'max %d nproc' % (
                                           self.num_processes))
            # this is enough to continue
            return resource_available
        else:
            resource_available['nproc'] = (True, '')

        return resource_available

    @contract(reasons_why_not=dict)
    def can_accept_job(self, reasons_why_not):
        resources = self.get_resources_status()
        some_missing = False
        for k, v in resources.items():
            if not v[0]:
                some_missing = True
                reasons_why_not[k] = v[1]
        if some_missing:
            return False
        return True

    def instance_job(self, job_id):
        assert len(self.sub_available) > 0
        name = sorted(self.sub_available)[0]
        self.sub_available.remove(name)
        assert not name in self.sub_processing
        self.sub_processing.add(name)
        sub = self.subs[name]
        self.job2subname[job_id] = name
        ares = sub.instance_job(job_id)
        return ares

    def host_failed(self, job_id):
        Manager.host_failed(self, job_id)
        self._clear(job_id)

    def job_failed(self, job_id, deleted_jobs):
        Manager.job_failed(self, job_id, deleted_jobs)
        self._clear(job_id)

    def job_succeeded(self, job_id):
        Manager.job_succeeded(self, job_id)
        self._clear(job_id)

    def _clear(self, job_id):
        assert job_id in self.job2subname
        name = self.job2subname[job_id]
        del self.job2subname[job_id]
        assert name in self.sub_processing
        assert name not in self.sub_available
        self.sub_processing.remove(name)
        self.sub_available.add(name)

    def cleanup(self):
        Manager.cleanup(self)
        n = len(self.processing2result)
        if n > 100:
            print('Cleaning up %d SGE jobs. Please be patient.' % n)
        for _, job in self.processing2result.items():
            job.delete_job()
