import unittest

from compmake import storage
from compmake.storage import use_filesystem
from compmake.jobs.storage import set_namespace, remove_all_jobs

class Simple(unittest.TestCase):
    
    def setUp(self):
        use_filesystem('Simple_db')
        set_namespace('Simple')
        remove_all_jobs()
            
    def testExists1(self):
        assert(not storage.db.is_cache_available('not-existent'))
    
    def testExists2(self):
        k = 'ciao'
        v = {'complex': 123}
        if storage.db.is_cache_available(k):
            storage.db.delete_cache(k)
        self.assertFalse(storage.db.is_cache_available(k))
        storage.db.set_cache(k, v)
        self.assertTrue(storage.db.is_cache_available(k))
        storage.db.delete_cache(k)
        self.assertFalse(storage.db.is_cache_available(k))
        storage.db.set_cache(k, v)
        storage.db.delete_cache(k)
        self.assertFalse(storage.db.is_cache_available(k))
        
    def testSearch(self):
        storage.db.set_cache('key1', 1)
        storage.db.set_cache('key2', 1)
        self.assertEqual([], storage.db.keys('ciao*'))
        self.assertEqual(['key1'], storage.db.keys('key1'))
        self.assertEqual(['key1'], storage.db.keys('*1'))
        self.assertEqual([], storage.db.keys('d*1'))
           
