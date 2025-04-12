# -*- coding: utf-8 -*-
"""
This is a clean __init__.py file for pytest.

Unlike nose, pytest doesn't require importing test modules in __init__.py.
This file intentionally does not import the test modules to avoid:
1. Circular import issues
2. Dependencies on nose (which uses the removed 'imp' module in Python 3.12)

To use this file:
1. Backup the original __init__.py: cp __init__.py __init__.py.nose
2. Replace it with this file: cp __init__.py.pytest __init__.py
3. Run tests with pytest: python -m pytest
4. If needed, restore the original for nose: cp __init__.py.nose __init__.py
"""

# Constants used for multiprocessing
_multiprocess_can_split_ = True  # Run parallel tests

# Import shared test utils if needed, but NOT the test modules themselves
# Note: Only import utilities that don't depend on nose
from compmake.structures import Cache, Job

# Version flag to indicate this is the pytest version
USING_PYTEST = True