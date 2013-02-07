import time
from compmake import comp

s = """
Same example as 'example.py', but for some values
of the parameters we are going to throw an exception. 
This will show how compmake deals with failure.

"""
print(s)


def func1(param1):
    print('func1(%s)' % param1)
    time.sleep(1) # ... which takes some time
    return param1

def func2(res1, param2):
    # we now add an exception
    if param2 == 11:
        raise Exception('11 is your unlucky number.')
    print('func2(%s, %s)' % (res1, param2))
    time.sleep(1) 
    return res1 + param1

def draw(res2):
    print('draw(%s)' % res2)

print('Defining jobs...')
for param1 in [1,2,3]:
    for param2 in [10,11,12]:
        res1 = comp(func1, param1)
        res2 = comp(func2, res1, param2)
        comp(draw, res2)

print('Ready to run...')

import compmake
if compmake.is_inside_compmake_script():
    print('Detected that we were imported by compmake.')
else:
    interactive = True
    if interactive:
        print('Presenting an interactive console')
        compmake.compmake_console()
    else:
        print('Running the computation in batch mode')
        compmake.batch_command('parmake n=4')
