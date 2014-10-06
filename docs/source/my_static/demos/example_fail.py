import time

print("""
Same example as 'example.py', but for some values
of the parameters we are going to throw an exception. 
This will show how compmake deals with failure.

""")

def funcA(param1):
    print('funcA(%s)' % param1)
    time.sleep(1) # ... which takes some time
    return param1

def funcB(res1, param2):
    # we now add an exception
    if param2 == 11:
        raise Exception('11 is your unlucky number.')
    print('funcB(%s, %s)' % (res1, param2))
    time.sleep(1) 
    return res1 + param1

def draw(res2):
    print('draw(%s)' % res2)

if __name__ == '__main__':
    from compmake import Context
    context = Context()
    
    for param1 in [1,2,3]:
        for param2 in [10,11,12]:
            res1 = context.comp(funcA, param1)
            res2 = context.comp(funcB, res1, param2)
            context.comp(draw, res2)

    import sys
    if len(sys.argv) == 1:
        print('Presenting an interactive console')
        context.compmake_console()
    else:
        print('Running the computation in batch mode')
        cmd = " ".join(sys.argv[1:])
        context.batch_command(cmd)
