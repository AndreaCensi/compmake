# -*- coding: utf-8 -*-
import inspect
import sys
from collections import namedtuple

# Create our own ArgSpec namedtuple to match the structure of the old inspect.ArgSpec
ArgSpec = namedtuple('ArgSpec', ['args', 'varargs', 'keywords', 'defaults'])

def get_arg_spec(function):
    """Compatibility wrapper for inspect.getargspec/getfullargspec"""
    if hasattr(inspect, 'getfullargspec'):
        spec = inspect.getfullargspec(function)
        # Convert to the old format using our ArgSpec namedtuple
        return ArgSpec(
            args=spec.args,
            varargs=spec.varargs,
            keywords=spec.varkw,
            defaults=spec.defaults
        )
    else:
        # For older Python versions
        return inspect.getargspec(function)