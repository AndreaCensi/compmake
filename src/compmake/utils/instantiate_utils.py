# -*- coding: utf-8 -*-
# Jan 14 copied from conf_tools
import traceback

from contracts import contract
from contracts.utils import indent


__all__ = [
    'import_name',
]


@contract(name='str')
def import_name(name):
    """
        Loads the python object with the given name.

        Note that "name" might be "module.module.name" as well.
    """
    try:
        return __import__(name, fromlist=['dummy'])
    except ImportError as e:
        # split in (module, name) if we can
        if '.' in name:
            tokens = name.split('.')
            field = tokens[-1]
            module_name = ".".join(tokens[:-1])

            if False:  # previous method
                pass
                # try:
                #     module = __import__(module_name, fromlist=['dummy'])
                # except ImportError as e:
                #     msg = ('Cannot load %r (tried also with %r):\n' %
                #            (name, module_name))
                #     msg += '\n' + indent(
                #         '%s\n%s' % (e, traceback.format_exc(e)), '> ')
                #     raise ValueError(msg)
                #
                # if not field in module.__dict__:
                #     msg = 'No field  %r\n' % field
                #     msg += ' found in %r.' % module
                #     raise ValueError(msg)
                #
                # return module.__dict__[field]
            else:
                # other method, don't assume that in "M.x", "M" is a module.
                # It could be a class as well, and "x" be a staticmethod.
                try:
                    module = import_name(module_name)
                except ImportError as e:
                    msg = ('Cannot load %r (tried also with %r):\n' %
                           (name, module_name))
                    msg += '\n' + indent(
                        '%s\n%s' % (e, traceback.format_exc()), '> ')
                    raise ValueError(msg)

                if not field in module.__dict__:
                    msg = 'No field %r\n' % field
                    msg += ' found in %r.' % module
                    raise ValueError(msg)

                f = module.__dict__[field]

                # "staticmethod" are not functions but descriptors, we need
                # extra magic
                if isinstance(f, staticmethod):
                    return f.__get__(module, None)
                else:
                    return f

        else:
            msg = 'Cannot import name %r.' % name
            msg += indent(traceback.format_exc(), '> ')
            raise ValueError(msg)
