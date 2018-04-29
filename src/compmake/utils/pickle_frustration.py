# -*- coding: utf-8 -*-
from contracts import contract
import os, sys
from contextlib import contextmanager


@contract(returns=dict)
def pickle_main_context_save():
    """ Remember who was the __main__ module """
    module = sys.modules['__main__']
    filename = module.__file__
    name = os.path.splitext(os.path.basename(filename))[0] 
    main_module = name
    main_path = os.path.realpath(os.path.dirname(filename))
    return dict(main_module=main_module, main_path=main_path)

@contextmanager
def pickle_main_context_load(c):
    main_path = c['main_path']
    main_module = c['main_module']
    
    try:
        if not main_path in sys.path: 
            sys.path.append(main_path)
    
        cur_main = sys.modules['__main__']
    
        try:
            m = __import__(main_module, fromlist=['dummy'])
            m.__name__ = '__main__'
            sys.modules['__main__'] = m
        except ImportError as e:
#             print('pickle_main_context_load: Cannot import %r: %s' 
#                   % (main_module, e))
            pass
        yield
        
    finally:
        sys.modules['__main__'] = cur_main    
    
