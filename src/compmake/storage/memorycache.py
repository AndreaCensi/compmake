# -*- coding: utf-8 -*-
import sys

__all__ = [
    'MemoryCache',
]


# noinspection PyArgumentList
class MemoryCache(object):

    def __init__(self, db, cache_values=True):
        self.data = {}
        self.db = db
        self.cache_values = cache_values
        self.keys_to_cache = ':job:'
        
    def __getitem__(self, key):
        if key in self.data:
            return self.data[key]
        ob = self.db.__getitem__(key)
        if self.should_cache(key):
            self.data[key] = ob
        return ob 
    
    def should_cache(self, key):
        if not self.cache_values:
            return False
        return self.keys_to_cache in key
        
    def __setitem__(self, key, value):
        # TODO: check value
        if self.should_cache(key):
            self.data[key] = value
        self.db[key] = value
            
    def __delitem__(self, key):
        if key in self.data:
            self.data.__delitem__(key)
        self.db.__delitem__(key)
        
    def __contains__(self, key):
        if key in self.data:
            return True
        else:
            return self.db.__contains__(key)
  
    def sizeof(self, key):
        # XXX: not recursive
        return sys.getsizeof(key)
    
    def keys(self):
        return self.db.keys() 
    

