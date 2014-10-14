def f(x): 
    print('processing %s' % x)

if __name__ == '__main__':
    from compmake import Context
    c = Context()
    for p in [42, 43, 44]:
        c.comp(f, x=p)
    c.batch_command('clean;parmake')

