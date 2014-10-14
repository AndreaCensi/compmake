def f(x): 
    print('f(x=%r)' % x)
    return x * 2

def schedule(context, params):
    print('schedule(context, params=%s)' % params.__repr__())
    for p in [42, 43, 44]:
        context.comp(f, x=p)

if __name__ == '__main__':
    from compmake import Context
    c = Context()
    c.comp_dynamic(schedule, params=[42, 43, 44])
    c.batch_command('clean;parmake echo=1 recurse=1')