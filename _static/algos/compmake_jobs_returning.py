def f(x): 
    return x * 2
def statistics(res): 
    return sum(res)
def schedule(context, params):
    jobs = [c.comp(f, x=p) for p in params]
    summary = c.comp(statistics, jobs)
    # returns a job "promise", not a value!
    return summary
def report(summary):
    print('The sum is: %r' % summary)
    
if __name__ == '__main__':
    from compmake import Context
    c = Context()
    summary = c.comp_dynamic(schedule, [42, 43, 44])
    c.comp(report, summary)
    c.batch_command('clean;parmake recurse=1')

