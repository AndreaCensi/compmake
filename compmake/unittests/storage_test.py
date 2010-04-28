import unittest

from compmake.storage import db

class Simple(unittest.TestCase):
    
    def testExists1(self):
        assert(not db.is_cache_available('not-existent'))
    
    def testExists2(self):
        k = 'ciao'
        v = {'complex': 123}
        if db.is_cache_available(k):
            db.delete_cache(k)
        self.assertFalse(db.is_cache_available(k))
        db.set_cache(k, v)
        self.assertTrue(db.is_cache_available(k))
        db.delete_cache(k)
        self.assertFalse(db.is_cache_available(k))
        db.set_cache(k, v)
        db.delete_cache(k)
        self.assertFalse(db.is_cache_available(k))
        
    def testSearch(self):
        db.set_cache('key1', 1)
        db.set_cache('key2', 1)
        self.assertEqual([], db.keys('ciao*'))
        self.assertEqual(['key1'], db.keys('key1'))
        self.assertEqual(['key1'], db.keys('*1'))
        self.assertEqual([], db.keys('d*1'))
           