from nose.tools import istest

from .compmake_test import CompmakeTest


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


@istest
class TestDynamic1(CompmakeTest):

    howmany = None  # used by cases()

    def test_dynamic1(self):
        values = self.cc.comp(cases, job_id='values')
        self.cc.comp_dynamic(generate_tsts, values, job_id='generate')

        # At this point we have generated only two jobs
        self.assertJobsEqual('all', ['generate', 'values'])
        
        # now we make them
        TestDynamic1.howmany = 3
        self.assert_cmd_success('make')

        # this will have created new jobs
        self.assertJobsEqual('all', ['generate', 'values', 'actual0', 'actual1', 'actual2', 'finish'])
        # ... still to do
        self.assertJobsEqual('todo', ['actual0', 'actual1', 'actual2', 'finish'])

        # we can make them
        self.assert_cmd_success('make')
        self.assertJobsEqual('done', ['generate', 'values', 'actual0', 'actual1', 'actual2', 'finish'])

        # Now let's suppose we re-run values and it generates different number of tests
        TestDynamic1.howmany = 2
        self.assert_cmd_success('clean values; make generate')

        # Now we should have on job less because actual2 was not re-defined
        self.assertJobsEqual('all', ['generate', 'values', 'actual0', 'actual1', 'finish'])
        # they should be all done, by the way
        self.assertJobsEqual('done', ['generate', 'values', 'actual0', 'actual1', 'finish'])

        # Now let's increase it to 4
        TestDynamic1.howmany = 4
        self.assert_cmd_success('clean values; make generate')

        self.assert_cmd_success('details finish')

        self.assertJobsEqual('all', ['generate', 'values', 'actual0', 'actual1', 'actual2', 'actual3', 'finish'])
        # some are done
        self.assertJobsEqual('done', ['generate', 'values', 'actual0', 'actual1', 'finish'])
        # but finish is not updtodate
        self.assertJobsEqual('uptodate', ['generate', 'values', 'actual0', 'actual1'])
        # some others are not
        self.assertJobsEqual('todo', ['actual2', 'actual3'])
