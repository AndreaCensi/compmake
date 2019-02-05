# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import datetime


__all__ = [
    'isodate_with_secs',
]


def isodate_with_secs():
    """ E.g., '2011-10-06-22:54:33' """
    now = datetime.datetime.now()
    date = now.isoformat('-')[:19]
    return date
