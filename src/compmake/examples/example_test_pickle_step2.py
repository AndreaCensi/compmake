# -*- coding: utf-8 -*-
from __future__ import print_function
from compmake.utils import safe_pickle_load

# module = sys.modules['__main__']

m = __import__('example_test_pickle', fromlist=['dummy'])
m.__name__ = '__main__'
print('module %r' % m)
import sys
sys.modules['__main__'] = m
filename ='f1.pickle' 
import compmake
x = compmake.utils.safe_pickle_load(filename)
print(x.__doc__)

