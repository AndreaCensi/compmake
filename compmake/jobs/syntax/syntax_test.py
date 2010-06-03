
from unittest import TestCase
from compmake.jobs.storage import set_namespace, remove_all_jobs, get_job_cache, \
    set_job_cache, all_jobs
from compmake.structures import Cache, UserError, CompmakeSyntaxError
from compmake.ui.ui import comp, parse_job_list, reset_jobs_definition_set

from compmake.storage import use_filesystem
import sys


def dummy():
    pass

class Test1(TestCase):
    
    def setUp(self):
        use_filesystem('test1_db')
        set_namespace('Test1')
        remove_all_jobs()

        reset_jobs_definition_set()
        
        self.jobs = [
                ('a', Cache.DONE),
                ('b', Cache.FAILED),
                ('c', Cache.NOT_STARTED),
                ('d', Cache.DONE),
                ('e', Cache.DONE),
                ('f', Cache.IN_PROGRESS),
                ('g', Cache.DONE),
                ('h', Cache.FAILED),
                ('i', Cache.DONE),
                ('ii', Cache.DONE),
                ('v_rangefinder_nonunif-plot_tensors_tex-0', Cache.DONE),
        ]
        
        for job_id, state in self.jobs:
            comp(dummy, job_id=job_id)
            cache = get_job_cache(job_id)
            cache.state = state
            set_job_cache(job_id, cache)

        self.all = set([job_id for job_id, state in self.jobs])
        select = lambda S: set([id for id, state in self.jobs if state == S])
        self.failed = select(Cache.FAILED)
        self.done = select(Cache.DONE)
        self.in_progress = select(Cache.IN_PROGRESS)
        self.not_started = select(Cache.NOT_STARTED)
         
    def selection(self, crit):
        return set([id for id, state in self.jobs if crit(id, state) ])
    
    def expandsTo(self, A, B):
        ''' A, B can be:
        - set or list: list of jobs
        - string: passed to expands_jobs
        - lambda: passed to selection()
        '''
        
        def expand_to_set(X):
            if isinstance(X, set):
                return X
            elif isinstance(X, list):
                return set(X)
            elif isinstance(X, type(lambda:0)):
                return self.selection(X)
            elif isinstance(X, str):
                return set(parse_job_list(X))
            else:
                assert False, 'Wrong type %s' % type(X)
                
        a = expand_to_set(A)
        b = expand_to_set(B)
        
        sys.stdout.write('Comparing:\n\t- %s\n\t- %s. \n' % (A, B))
        
        self.assertEqual(a, b)
    
    def syntaxError(self, s):
        self.assertRaises(CompmakeSyntaxError, parse_job_list, s)
    
    def userError(self, s):
        self.assertRaises(UserError, parse_job_list, s)
    
    def testCatchErrors(self): 
        self.syntaxError('not')    
        self.syntaxError('all not e')
        self.syntaxError('all not')
        self.syntaxError('all not')    
        self.syntaxError('all in')
        self.syntaxError('in $all')

    def testSpecial(self):
        ''' Test that the special variables work'''
        self.expandsTo('  ', set())
        self.expandsTo('all', self.all)
        self.expandsTo('failed', self.failed)
        self.expandsTo('done', self.done)
        self.expandsTo('DONE', self.done)
        self.expandsTo('in_progress', self.in_progress)
        
    def testBasicUnion(self):
        ''' Testing basic union operator '''
        self.expandsTo('failed e', self.failed.union('e'))
        self.expandsTo('e failed', self.failed.union('e'))
    
    def testNot(self):
        self.expandsTo('not failed',
                       lambda job, state: state != Cache.FAILED) #@UnusedVariable
        self.expandsTo('all except failed',
                       lambda job, state: state != Cache.FAILED) #@UnusedVariable

        all_not_e = self.selection(lambda job, state: job != 'e') #@UnusedVariable
        self.expandsTo('not e', all_not_e)
        self.expandsTo('not e*', all_not_e)
        self.expandsTo('all except e', all_not_e)
        self.expandsTo('not not e', ['e'])
        self.expandsTo('not not all', 'all')
        self.expandsTo('not all', [])
        self.expandsTo('not all except all', [])
        self.expandsTo('not e except not e', [])
        self.expandsTo('not a b c except not a b c', [])
        self.expandsTo('not c except a ', 'not a c')
        self.expandsTo('a in c  ', [])
        self.expandsTo('a in all  ', 'a')
        self.expandsTo('all in all  ', 'all')
        
    
    def testIntersection(self):    
        self.expandsTo('a b in a b c', ['a', 'b'])
        self.expandsTo('a b c in d e f', [])
        
    
    def tearDown(self):
        pass
