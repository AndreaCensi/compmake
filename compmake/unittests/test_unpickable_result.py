from .. import storage, compmake_status_embedded, set_compmake_status
from ..jobs import set_namespace
from ..storage import use_filesystem
from ..structures import SerializationError
import unittest


def f1():
    print("done")
    return lambda x: None #@UnusedVariable


class TestUnpickable(unittest.TestCase):

    def setUp(self):
        set_compmake_status(compmake_status_embedded)
        use_filesystem('unpickable')
        set_namespace('unpickable')
        for key in storage.db.keys('*'):
            storage.db.delete(key)

    def test_unpickable(self):
        self.assertRaises(SerializationError, self.add_and_execute, f1)

    def add_and_execute(self, function):
        from compmake import comp, batch_command
        comp(function)
        batch_command('clean')
        batch_command('make')
