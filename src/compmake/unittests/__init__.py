# -*- coding: utf-8 -*-
_multiprocess_can_split_ = True # Run parallel mcdp_lang_tests
from .compmake_test import *

# Load all mcdp_lang_tests (helps with nose multiprocess)
from . import test_blocked
from . import test_invalid_functions
from . import test_more
from . import test_priorities
from . import test_storage
from . import test_progress
from . import test_syntax
from . import test_unpickable_result
