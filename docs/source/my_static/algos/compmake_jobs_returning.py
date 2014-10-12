def f(x): 
    print('f(x=%r)' % x)
    return x * 2

def statistics(res): 
    print('statistics(res=%s)' % res.__repr__())
    return sum(res)

def schedule(context, params):
    print('schedule(context, params=%s)' % params.__repr__())
    jobs = [context.comp(f, x=p) for p in params]
    summary = context.comp(statistics, jobs)
    # returns a job "promise", not a value!
    return summary

def report(summary):
    print('report(summary=%r)' % summary)
    
if __name__ == '__main__':
    from compmake import Context
    c = Context()
    summary = c.comp_dynamic(schedule, [42, 43, 44])
    c.comp(report, summary)
    c.batch_command('clean;parmake echo=1 recurse=1')
