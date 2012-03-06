from . import CompmakeTest
from .. import CompmakeGlobalState


class Simple(CompmakeTest):

    def mySetUp(self):
        pass

    def testExists1(self):
        assert(not CompmakeGlobalState.db.exists('not-existent')) #@UndefinedVariable

    def testExists2(self):
        k = 'ciao'
        v = {'complex': 123}
        db = CompmakeGlobalState.db
        if db.exists(k):
            db.delete(k)
        self.assertFalse(db.exists(k))
        db.set(k, v)
        self.assertTrue(db.exists(k))
        db.delete(k)
        self.assertFalse(db.exists(k))
        db.set(k, v)
        db.delete(k)
        self.assertFalse(db.exists(k))

    def testSearch(self):
        db = CompmakeGlobalState.db
        search = lambda pattern: list(db.keys(pattern))
        self.assertEqual([], search('*'))
        db.set('key1', 1)
        db.set('key2', 1)
        self.assertEqual([], search('ciao*'))
        self.assertEqual(['key1'], search('key1'))
        self.assertEqual(['key1'], search('*1'))
        self.assertEqual([], search('d*1'))

