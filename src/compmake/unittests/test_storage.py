from . import CompmakeTest
from compmake.utils.wildcards import wildcard_to_regexp
from compmake.state import get_compmake_db
 

class Simple(CompmakeTest):

    def mySetUp(self):
        pass

    def testExists1(self):
        db = get_compmake_db()
        key = 'not-existent'
        assert(not key in db)

    def testExists2(self):
        k = 'ciao'
        v = {'complex': 123}
        db = get_compmake_db()
        if k in db:
            del db[k]
        self.assertFalse(k in db)
        db[k] = v
        self.assertTrue(k in db)
        del db[k]
        self.assertFalse(k in db)
        db[k] = v
        del db[k]
        self.assertFalse(k in db)

    def testSearch(self):
        db = get_compmake_db()
        
        def search(pattern):
            r = wildcard_to_regexp(pattern)
            for k in db.keys():
                if r.match(k):
                    yield k
            
        self.assertEqual([], list(search('*')))
        db['key1'] = 1
        db['key2'] = 1
        self.assertEqual([], list(search('ciao*')))
        self.assertEqual(['key1'], list(search('key1')))
        self.assertEqual(['key1'], list(search('*1')))
        self.assertEqual([], list(search('d*1')))

