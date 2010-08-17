import unittest

from compmake import storage
from compmake.storage import use_filesystem
from compmake.jobs.storage import set_namespace, remove_all_jobs

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
        self.assertEqual([], storage.db.keys('*'))
        storage.db.set('key1', 1)
        storage.db.set('key2', 1)
        self.assertEqual([], storage.db.keys('ciao*'))
        self.assertEqual(['key1'], storage.db.keys('key1'))
        self.assertEqual(['key1'], storage.db.keys('*1'))
        self.assertEqual([], storage.db.keys('d*1'))
           
