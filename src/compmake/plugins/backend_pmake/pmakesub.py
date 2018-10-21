# -*- coding: utf-8 -*-
import multiprocessing
import signal
import traceback
from multiprocessing import TimeoutError

from compmake.exceptions import CompmakeBug, HostFailed, JobFailed, JobInterrupted
from compmake.jobs.manager import AsyncResultInterface
from compmake.jobs.result_dict import result_dict_raise_if_error
from contracts import check_isinstance, indent
from future.moves.queue import Empty

__all__ = [
    'PmakeSub',
]


class PmakeSub(object):
    EXIT_TOKEN = 'please-exit'

    def __init__(self, name, signal_queue, signal_token, write_log=None):
        self.name = name

        self.job_queue = multiprocessing.Queue()
        self.result_queue = multiprocessing.Queue()
        self.proc = multiprocessing.Process(target=pmake_worker,
                                            args=(self.name,
                                                  self.job_queue,
                                                  self.result_queue,
                                                  signal_queue,
                                                  signal_token,
                                                  write_log))
        self.proc.start()

    def terminate(self):
        self.job_queue.put(PmakeSub.EXIT_TOKEN)
        self.job_queue.close()
        self.result_queue.close()
        self.job_queue = None
        self.result_queue = None

    def apply_async(self, function, arguments):
        self.job_queue.put((function, arguments))
        self.last = PmakeResult(self.result_queue)
        return self.last


def pmake_worker(name, job_queue, result_queue, signal_queue, signal_token,
                 write_log=None):
    if write_log:
        f = open(write_log, 'w')

        def log(s):
            f.write('%s: ' % name)
            f.write(s)
            f.write('\n')
            f.flush()
    else:
        def log(s):
            pass

    log('started pmake_worker()')
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    def put_result(x):
        log('putting result in result_queue..')
        result_queue.put(x, block=True)
        if signal_queue is not None:
            log('putting result in signal_queue..')
            signal_queue.put(signal_token, block=True)
        log('(done)')

    try:
        while True:
            log('Listening for job')
            job = job_queue.get(block=True)
            log('got job: %s' % str(job))
            if job == PmakeSub.EXIT_TOKEN:
                break
            function, arguments = job
            try:
                result = function(arguments)
            except JobFailed as e:
                log('Job failed, putting notice.')
                log('result: %s' % str(e))  # debug
                put_result(e.get_result_dict())
            except JobInterrupted as e:
                log('Job interrupted, putting notice.')
                put_result(dict(abort=str(e)))  # XXX
            except CompmakeBug as e:  # XXX :to finish
                log('CompmakeBug')
                put_result(e.get_result_dict())
            else:
                log('result: %s' % str(result))
                put_result(result)

            log('...done.')

            # except KeyboardInterrupt: pass
    except BaseException as e:
        reason = 'aborted because of uncaptured:\n' + indent(
                traceback.format_exc(), '| ')
        mye = HostFailed(host="???", job_id="???",
                         reason=reason, bt=traceback.format_exc())
        log(str(mye))
        put_result(mye.get_result_dict())
    except:
        mye = HostFailed(host="???", job_id="???",
                         reason='Uknown exception (not BaseException)',
                         bt="not available")
        log(str(mye))
        put_result(mye.get_result_dict())
        log('(put)')

    if signal_queue is not None:
        signal_queue.close()
    result_queue.close()
    log('clean exit.')


class PmakeResult(AsyncResultInterface):
    """ Wrapper for the async result object obtained by pool.apply_async """

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

    def get(self, timeout=0):  # @UnusedVariable
        if self.result is None:
            try:
                self.result = self.result_queue.get(block=True,
                                                    timeout=timeout)
            except Empty as e:
                raise TimeoutError(e)

        check_isinstance(self.result, dict)
        result_dict_raise_if_error(self.result)
        return self.result
