# -*- coding: utf-8 -*-
import os

from .qacct import JobNotRunYet, get_qacct
from compmake.jobs import AsyncResultInterface, result_dict_raise_if_error
from compmake.exceptions import CompmakeBug, HostFailed
from compmake.ui import error
from compmake.utils import safe_pickle_load, which
from contracts import all_disabled, indent
from system_cmd import CmdException, system_cmd_result


__all__ = [
    'SGESub',
]


class SGESub():
    def __init__(self, name, db, spool):
        self.name = name
        self.job_id = None
        self.db = db
        self.res = None
        self.spool = spool

    def delete_job(self):
        self.res.delete_job()

    def instance_job(self, job_id):
        self.res = SGEJob(job_id, self.db, spool=self.spool)
        return self.res


class SGEJob(AsyncResultInterface):
    compmake_bin = None

    @staticmethod
    def get_compmake_bin():
        """ Returns the path to the compmake executable. """
        if SGEJob.compmake_bin is None:
            compmake_bin = which('compmake')
            SGEJob.compmake_bin = compmake_bin
        return SGEJob.compmake_bin

    def __init__(self, job_id, db, spool):
        self.job_id = job_id
        self.db = db
        self.execute(spool=spool)

    def delete_job(self):
        # cmd = ['qdel', self.sge_id]
        cmd = ['qdel', self.sge_job_name]
        cwd = os.path.abspath(os.getcwd())
        # TODO: check errors
        try:
            _ = system_cmd_result(cwd, cmd,
                                  display_stdout=False,
                                  display_stderr=False,
                                  raise_on_error=True,
                                  capture_keyboard_interrupt=False)
        except CmdException as e:
            error('Error while deleting job:\n%s' % e)

    def execute(self, spool):
        db = self.db
        # Todo: check its this one

        storage = os.path.abspath(db.basepath)

        # create a new spool directory for each execution
        # otherwise we get confused!

        self.stderr = os.path.join(spool, '%s.stderr' % self.job_id)
        self.stdout = os.path.join(spool, '%s.stdout' % self.job_id)
        self.retcode = os.path.join(spool, '%s.retcode' % self.job_id)
        self.out_results = os.path.join(spool,
                                        '%s.results.pickle' % self.job_id)

        if os.path.exists(self.stderr):
            os.remove(self.stderr)

        if os.path.exists(self.stdout):
            os.remove(self.stdout)

        if os.path.exists(self.retcode):
            os.remove(self.retcode)

        if os.path.exists(self.out_results):
            os.remove(self.out_results)

        options = []
        cwd = os.path.abspath(os.getcwd())
        variables = dict(SGE_O_WORKDIR=cwd,
                         PYTHONPATH=os.getenv('PYTHONPATH', '') + ':' + cwd)

        # nice-looking name
        self.sge_job_name = 'cm%s-%s' % (os.getpid(), self.job_id)
        # Note that we get the official "id" later and we store it in
        # self.sge_id
        options.extend(
            ['-v', ",".join('%s=%s' % x for x in variables.items())])
        # XXX: spaces
        options.extend(['-e', self.stderr])
        options.extend(['-o', self.stdout])
        options.extend(['-N', self.sge_job_name])
        options.extend(['-wd', cwd])

        options.extend(['-V'])  # pass all environment

        options.extend(['-terse'])

        compmake_bin = SGEJob.get_compmake_bin()

        compmake_options = [
            compmake_bin, storage,
            '--retcodefile', self.retcode,
            '--status_line_enabled', '0',
            '--colorize', '0',
            '-c',
            '"make_single out_result=%s %s"' % (self.out_results, self.job_id),
        ]

        if not all_disabled():
            compmake_options += ['--contracts']

        # XXX: spaces in variable out_result

        write_stdin = ' '.join(compmake_options)

        cmd = ['qsub'] + options

        res = system_cmd_result(cwd, cmd,
                                display_stdout=False,
                                display_stderr=True,
                                raise_on_error=True,
                                write_stdin=write_stdin,
                                capture_keyboard_interrupt=False)

        self.sge_id = res.stdout.strip()

        self.already_read = False
        self.npolls = 0

        self.told_you_ready = False

    def ready(self):
        if self.told_you_ready:
            raise CompmakeBug('should not call ready() twice')

        if self.npolls % 20 == 1:
            try:
                qacct = get_qacct(self.sge_id)
                # print('job: %s sgejob: %s res: %s' % (self.job_id,
                # self.sge_id, qacct))
                if 'failed' in qacct and qacct['failed'] != '0':
                    reason = 'Job schedule failed: %s\n%s' % (
                    qacct['failed'], qacct)
                    raise HostFailed(host="xxx",
                                     job_id=self.job_id, reason=reason,
                                     bt="")  # XXX

            except JobNotRunYet:
                qacct = None
                pass
        else:
            qacct = None

        self.npolls += 1

        if os.path.exists(self.retcode):
            self.told_you_ready = True
            return True
        else:
            if qacct is not None:
                msg = 'The file %r does not exist but it looks like the job ' \
                      'is done' % self.retcode
                msg += '\n %s ' % qacct
                # All right, this is simply NFS that is not updated yet
                # raise CompmakeBug(msg)

            return False

    def get(self, timeout=0):  # @UnusedVariable
        if not self.told_you_ready:
            raise CompmakeBug("I didnt tell you it was ready.")
        if self.already_read:
            msg = 'Compmake BUG: should not call twice.'
            raise CompmakeBug(msg)
        self.already_read = True

        assert os.path.exists(self.retcode)
        ret_str = open(self.retcode, 'r').read()
        try:
            ret = int(ret_str)
        except ValueError:
            msg = 'Could not interpret file %r: %r.' % (self.retcode, ret_str)
            raise HostFailed(host='localhost',
                             job_id=self.job_id, reason=msg, bt='')
            #
        #
        #         raise HostFailed(host="xxx",
        #                                      job_id=self.job_id,
        # reason=reason, bt="")  # XXX
        #

        try:
            stderr = open(self.stderr, 'r').read()
            stdout = open(self.stdout, 'r').read()

            stderr = 'Contents of %s:\n' % self.stderr + stderr
            stdout = 'Contents of %s:\n' % self.stdout + stdout

            # if ret == CompmakeConstants.RET_CODE_JOB_FAILED:
            #                 msg = 'SGE Job failed (ret: %s)\n' % ret
            #                 msg += indent(stderr, '| ')
            #                 # mark_as_failed(self.job_id, msg, None)
            #                 raise JobFailed(msg)
            #             elif ret != 0:
            #                 msg = 'SGE Job failed (ret: %s)\n' % ret
            #                 error(msg)
            #                 msg += indent(stderr, '| ')
            #                 raise JobFailed(msg)

            if not os.path.exists(self.out_results):
                msg = 'job succeeded but no %r found' % self.out_results
                msg += '\n' + indent(stderr, 'stderr')
                msg += '\n' + indent(stdout, 'stdout')
                raise CompmakeBug(msg)

            res = safe_pickle_load(self.out_results)
            result_dict_raise_if_error(res)
            return res
        finally:
            fs = [self.stderr, self.stdout, self.out_results, self.retcode]
            for filename in fs:
                if os.path.exists(filename):
                    os.unlink(filename)
                    
