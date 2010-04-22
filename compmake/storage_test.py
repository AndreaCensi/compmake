import unittest

from compmake.storage import \
    get_cache, delete_cache, is_cache_available, set_cache

class Simple(unittest.TestCase):
    
    def testExists1(self):
        assert(not is_cache_available('not-existent'))
    
    def testExists2(self):
        k = 'ciao'
        v = {'complex': 123}
        delete_cache(k)
        self.assertFalse(is_cache_available(k))
        set_cache(k, v)
        self.assertTrue(is_cache_available(k))
        delete_cache(k)
        self.assertFalse(is_cache_available(k))
        set_cache(k, v)
        delete_cache(k)
        self.assertFalse(is_cache_available(k))
        
        