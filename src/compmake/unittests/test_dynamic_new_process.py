# -*- coding: utf-8 -*-
import pytest
from .pytest_base import CompmakeTestBase
from .mockup import mockup_recursive_5

class TestDynamicNewProcess(CompmakeTestBase):

    @pytest.mark.skip(reason="new_process=1 has pickle compatibility issues with the dynamic __init__.py swap in the test runner")
    def test_make_new_process(self):
        mockup_recursive_5(self.cc)
        self.assert_cmd_success('make recurse=1 new_process=1;ls')