# -*- coding: utf-8 -*-
from compmake import logger

from .safe_write import *
from .wildcards import *
from .coloredterm import *
from .terminal_size import *

from .strings_with_escapes import *
from .capture import *
from .values_interpretation import *
from .debug_pickler import *
from .time_track import *
from .system_stats import *
from .proctitle import *
from .duration_hum import *
from .system_stats import *

from .safe_pickle import * 
from .frozen import *
from .memoize_imp import *

from .instantiate_utils import *
from .format_exceptions import * 
from .which_imp import *
from .timedate import *
from .filesystem_utils import *

from .colored import *
from .pickling_utils import *
from .docstring import *
from .friendly_path_imp import *

# def find_print_statements():
#     import sys
#     
#     class TracePrints(object):
#         def __init__(self):    
#             
#             self.stdout = sys.stdout
#         
#         def write(self, s):
#             self.stdout.write("Writing %r\n" % s)
#             import traceback
#             traceback.print_stack(file=self.stdout)
# 
#     sys.stdout = TracePrints()
