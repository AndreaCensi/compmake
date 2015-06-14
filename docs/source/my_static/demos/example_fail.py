
print("""\
This demo 'example_fail.py' is the same as 'example.py', but for some values of the \
parameters we are going to throw an exception. This will show how Compmake \
deals with failure.""")

def funcA(param_a):
    print('funcA(%r)' % param_a)
    return param_a

def funcB(res1, param_b):
    print('funcB(%r, %r)' % (res1, param_b))
    # we now add an exception
    if param_b == 11:
        msg = 'Exception raised for b = %d.' % param_b
        raise Exception(msg)
    return res1 + param_b

def draw(res2):
    print('draw(%r)' % res2) 

if __name__ == '__main__':
    from compmake import Context
    context = Context()
    
    for param_a in [1,2,3]:
        for param_b in [10,11,12]:
            context.comp_prefix('a%s-b%s' % (param_a, param_b))
            res1 = context.comp(funcA, param_a, job_id='preparing')
            res2 = context.comp(funcB, res1, param_b, job_id='computing')
            context.comp(draw, res2, job_id='drawing')

    import sys
    if len(sys.argv) == 1:
        print('Presenting an interactive console')
        context.compmake_console()
    else:
        print('Running the computation in batch mode')
        cmd = " ".join(sys.argv[1:])
        try:
            context.batch_command(cmd)
        except Exception as e:
            print('Command failed: %s' % e)
