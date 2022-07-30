from zuper_commons import ZLogger

logger = ZLogger(__name__)

from .capture import *
from .coloredterm import *
from .docstring import *
from .format_exceptions import *
from .frozen import *
from .get_memory_cgroup import *

# from .instantiate_utils import *
from .memoize_imp import *
from .pickling_utils import *
from .proctitle import *
from .safe_pickle import *
from .strings_with_escapes import *
from .system_stats import *
from .system_stats import *
from .terminal_size import *
from .time_track import *
from .timedate import *
from .values_interpretation import *
from .which_imp import *
from .table_formatter import *

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
