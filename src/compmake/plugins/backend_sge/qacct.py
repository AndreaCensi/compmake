# -*- coding: utf-8 -*-
from system_cmd import system_cmd_result
import os

__all__ = [
    'JobNotRunYet',
    'get_qacct',
]


class JobNotRunYet(Exception):
    pass


def get_qacct(sge_id):
    """ 
        Only provides results if the job already rann.
    
        Raises JobNotRunYet if the job didn't run.
    """
    cmd = ['qacct', '-j', sge_id]
    cwd = os.getcwd()
    res = system_cmd_result(cwd, cmd,
                            display_stdout=False,
                            display_stderr=False,
                            raise_on_error=False,
                            capture_keyboard_interrupt=False)
    if res.ret == 1:
        if 'startup' in res.stderr or 'startup' in res.stdout:
            # /opt/sge6/default/common/accounting: No such file or directory
            # no jobs running since startup
            raise JobNotRunYet(sge_id)
        if 'not found' in res.stderr:
            # todo
            raise JobNotRunYet(sge_id)
        raise Exception('qcct failed: %s' % res)
    if res.ret != 0:
        raise Exception('qcct failed: %s' % res)
    values = {}
    for line in res.stdout.split('\n'):
        tokens = line.split()
        if len(tokens) >= 2:  # XXX
            k = tokens[0]
            v = " ".join(tokens[1:])
            if k == 'failed':
                v = tokens[1]
            values[k] = v
    return values
