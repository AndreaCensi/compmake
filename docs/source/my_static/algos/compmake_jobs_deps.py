def f(x): 
    print('f(x=%r)' % x)
    return x * 2

def statistics(res): 
    print('statistics(res=%s)' % res.__repr__())
    return sum(res)
    
def report(val):
    print('The sum is: %r' % val)

if __name__ == '__main__':
    from compmake import Context
    c = Context()
    params = [42, 43, 44]
    jobs = [c.comp(f, x=p) for p in params]
    summary = c.comp(statistics, jobs)
    c.comp(report, summary)
    c.batch_command('clean;parmake echo=1')

    