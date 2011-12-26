from .. import storage
from ..jobs import set_namespace
from ..storage import use_filesystem
import unittest


class Simple(unittest.TestCase):

    def setUp(self):
        use_filesystem('Simple_db')
        set_namespace('Simple')
        for key in storage.db.keys('*'):
            storage.db.delete(key)

    def testExists1(self):
        assert(not storage.db.exists('not-existent'))

    def testExists2(self):
        k = 'ciao'
        v = {'complex': 123}
        if storage.db.exists(k):
            storage.db.delete(k)
        self.assertFalse(storage.db.exists(k))
        storage.db.set(k, v)
        self.assertTrue(storage.db.exists(k))
        storage.db.delete(k)
        self.assertFalse(storage.db.exists(k))
        storage.db.set(k, v)
        storage.db.delete(k)
        self.assertFalse(storage.db.exists(k))

    def testSearch(self):
        search = lambda pattern: list(storage.db.keys(pattern))

        self.assertEqual([], search('*'))
        storage.db.set('key1', 1)
        storage.db.set('key2', 1)
        self.assertEqual([], search('ciao*'))
        self.assertEqual(['key1'], search('key1'))
        self.assertEqual(['key1'], search('*1'))
        self.assertEqual([], search('d*1'))

