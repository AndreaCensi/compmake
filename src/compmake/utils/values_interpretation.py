# -*- coding: utf-8 -*-
__all__ = [
    'interpret_strings_like',
]


def interpret_strings_like(args, reference_value):
    if not isinstance(args, list):
        args = [args]

    if isinstance(reference_value, str):
        value = " ".join(args)
    elif isinstance(reference_value, bool):
        if len(args) > 1:
            raise ValueError('Too many arguments for bool.')
        try:
            value = eval(args[0])
        except:
            raise ValueError('Could not parse %s ' % args[0])
        value = bool(value)

    elif isinstance(reference_value, int):
        if len(args) > 1:
            raise ValueError('Too many arguments for int.')
        value = int(args[0])
    elif isinstance(reference_value, float):
        if len(args) > 1:
            raise ValueError('Too many arguments for float.')
        value = float(args[0])
    else:
        # XXX: security risk?
        try:
            value = eval(args[0])
        except:
            raise ValueError('Could not parse %s ' % args[0])

    return value

