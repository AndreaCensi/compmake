import unittest

from compmake.storage import db

class Simple(unittest.TestCase):
    
    def testExists1(self):
        assert(not db.is_cache_available('not-existent'))
    
    def testExists2(self):
        k = 'ciao'
        v = {'complex': 123}
        db.delete_cache(k)
        self.assertFalse(db.is_cache_available(k))
        db.set_cache(k, v)
        self.assertTrue(db.is_cache_available(k))
        db.delete_cache(k)
        self.assertFalse(db.is_cache_available(k))
        db.set_cache(k, v)
        db.delete_cache(k)
        self.assertFalse(db.is_cache_available(k))
        
        