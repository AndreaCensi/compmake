# -*- coding: utf-8 -*-
from compmake.exceptions import UserError
from compmake.utils import which
from contracts.utils import raise_wrapped

__all__ = [
    'check_sge_environment',
]


def check_sge_environment():
    msg_install = (
        " Please install SGE properly. "
    )
    try:
        _ = which('qsub')
    except ValueError as e:
        msg = 'Program "qsub" not available.\n'
        msg += msg_install
        raise_wrapped(UserError, e, msg)

