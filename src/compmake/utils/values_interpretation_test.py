# -*- coding: utf-8 -*-
from unittest import TestCase

from . import interpret_strings_like


class InterpretTest(TestCase):
    def test_bool(self):
        """ Testing boolean interpretation"""
        m = interpret_strings_like
        abool = True
        self.assertEqual(True, m('True', abool))
        self.assertEqual(False, m('False', abool))
        self.assertEqual(True, m('True', abool))
        self.assertEqual(False, m('False', abool))
        self.assertEqual(True, m('1', abool))
        self.assertEqual(False, m('0', abool))
        self.assertRaises(ValueError, m, '', abool)
        self.assertRaises(ValueError, m, 'a', abool)
