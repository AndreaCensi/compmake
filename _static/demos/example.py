import time
from compmake import comp

# A few functions representing a complex workflow
def func1(param1):
    print('func1(%s)' % param1)
    time.sleep(1) # ... which takes some time
    return param1

def func2(res1, param2):
    print('func2(%s, %s)' % (res1, param2))
    time.sleep(1) # ... which takes some time
    return res1 + param1

def draw(res2):
    print('draw(%s)' % res2)

# A typical pattern: you want to try 
# many combinations of parameters
for param1 in [1,2,3]:
    for param2 in [10,11,12]:
        # Simply use "y = comp(f, x)" whenever
        # you would have used "y = f(x)".
        res1 = comp(func1, param1)
        # You can use return values as well.
        res2 = comp(func2, res1, param2)
        comp(draw, res2)

# At this point, nothing has been run yet.
# There are different options on how to run the computation,
# depending on how much fine-grained control you want,
# and if you want an interactive or batch experience.

# Now, a few options to run this:
# 1) Call this file using the compmake program:
#  $ compmake example
#  and then run "make" at the prompt.
import compmake
if compmake.is_inside_compmake_script():
    print('Detected that we were imported by compmake.')
    # We were called by the "compmake" program. 
    # It will take care of presenting a console to the user 
else:
    interactive = True
    # 2) Run the console ourselves
    if interactive:
        print('Presenting an interactive console')
        compmake.compmake_console()
    # 3) Or just run the computation in batch mode:
    else:
        print('Running the computation in batch mode')
        compmake.batch_command('parmake n=4')
