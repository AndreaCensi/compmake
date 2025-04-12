#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Simple test script to verify pytest setup works.
"""

import os
import sys
import pytest
from tempfile import mkdtemp
from shutil import rmtree

# Add the src directory to the path so we can import compmake modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from compmake import set_compmake_config
from compmake.context import Context
from compmake.storage import StorageFilesystem

class TestSimple:
    """A minimal test to verify pytest fixtures work."""
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Setup and teardown for each test."""
        self.root0 = mkdtemp()
        self.root = os.path.join(self.root0, 'compmake')
        self.db = StorageFilesystem(self.root, compress=True)
        self.cc = Context(db=self.db)
        set_compmake_config('interactive', False)
        
        yield  # This is where the test runs
        
        if os.path.exists(self.root0):
            rmtree(self.root0)
    
    def test_basic(self):
        """Basic test that should always pass."""
        assert True
        
    def test_context(self):
        """Test that the context was created properly."""
        assert self.cc is not None
        assert self.db is not None

if __name__ == "__main__":
    # Run the tests directly
    exit_code = pytest.main(["-xvs", __file__])
    sys.exit(exit_code)