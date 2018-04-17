# -*- coding: utf-8 -*-
from .compmake_test import CompmakeTest
from nose.tools import istest



def cases():
    """ Note this uses TestDynamic1.howmany """
    howmany = TestDynamic1.howmany
    assert isinstance(howmany, int)
    print('returned %d cases' % howmany)
    return range(howmany)

def actual_tst(value):
    print('actual_tst(value)')
    return value * 2

def generate_tsts(context, values):
    res = []
    for i, v in enumerate(values):
        res.append(context.comp(actual_tst, v, job_id='actual%d' % i))
    return context.comp(finish, res)

def finish(values):
    return sum(values)

def mockup_dynamic1(context):
    values = context.comp(cases, job_id='values')
    context.comp_dynamic(generate_tsts, values, job_id='generate')

@istest
class TestDynamic1(CompmakeTest):

    howmany = None  # used by cases()

    def test_dynamic1_cleaning(self):
        mockup_dynamic1(self.cc)
        # At this point we have generated only two jobs
        self.assertJobsEqual('all', ['generate', 'values'])
        
        # now we make them
        TestDynamic1.howmany = 3
        self.assert_cmd_success('ls')
        self.assert_cmd_success('make')
        self.assert_cmd_success('ls')

        # this will have created new jobs
        self.assertJobsEqual('all', ['generate', 'values', 'actual0', 
                                     'actual1', 'actual2', 'generate-finish'])
        # ... still to do
        self.assertJobsEqual('todo', ['actual0', 'actual1', 'actual2', 
                                      'generate-finish'])

        # we can make them
        self.assert_cmd_success('make')
        self.assert_cmd_success('ls')
        self.assertJobsEqual('done', ['generate', 'values', 
                                      'actual0', 'actual1', 'actual2', 
                                      'generate-finish'])

        # Now let's suppose we re-run values and it generates different number of mcdp_lang_tests

        # Now let's increase it to 4
        TestDynamic1.howmany = 4
                
        self.assert_cmd_success('clean values; make generate')
        self.assert_cmd_success('ls reason=1')

        self.assertJobsEqual('all', ['generate', 'values', 'actual0', 'actual1', 'actual2', 'actual3', 'generate-finish'])
        # some are done
        self.assertJobsEqual('done', ['generate', 'values', 'actual0', 'actual1', 'actual2', 'generate-finish'])
        # but finish is not updtodate
        self.assertJobsEqual('uptodate', ['generate', 'values', 'actual0', 'actual1', 'actual2'])
        # some others are not
        self.assertJobsEqual('todo', [ 'actual3'])


        # now 2 jobs
        TestDynamic1.howmany = 2
        self.assert_cmd_success('clean values')
        self.assert_cmd_success('ls')
        self.assert_cmd_success('make generate')
        self.assert_cmd_success('ls')
        
        # Now we should have on job less because actual2 and 3 was not re-defined
        self.assertJobsEqual('all', ['generate', 'values', 'actual0', 
                                     'actual1', 'generate-finish'])
        # they should be all done, by the way
        self.assertJobsEqual('done', ['generate', 'values', 'actual0', 
                                      'actual1', 'generate-finish'])
