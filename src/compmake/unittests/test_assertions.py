from . import compmake_environment
# from ..structures import Cache
# from ..jobs import get_job_cache


def job_success(*args, **kwargs):
    pass


def job_failure(*args, **kwargs):  # @UnusedVariable
    assert False


@compmake_environment
def test_order():
    from compmake import comp, batch_command
    # make A -> B(fail) -> C
    for i in range(10):
        comp(job_failure, job_id='F%d' % i)
    batch_command('parmake n=2')

