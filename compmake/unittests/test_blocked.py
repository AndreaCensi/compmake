from compmake.unittests.compmake_test import  compmake_environment
from compmake.structures import Cache
from compmake.jobs.storage import get_job_cache


def job_success(*args, **kwargs):
    pass


def job_failure(*args, **kwargs):
    raise ValueError('This job fails')


def check_job_states(**expected):
    for job_id, expected_status in expected.items():
        status = get_job_cache(job_id).state
        if status != expected_status:
            msg = ('For job %r I expected %s but got %s.' %
                   (job_id, expected_status, status))
            raise Exception(msg)


@compmake_environment
def test_order():
    from compmake import comp, batch_command
    # make A -> B(fail) -> C
    A = comp(job_success, job_id='A')
    B = comp(job_failure, A, job_id='B')
    comp(job_success, B, job_id='C')
    batch_command('make')

    check_job_states(A=Cache.DONE, B=Cache.FAILED, C=Cache.BLOCKED)

