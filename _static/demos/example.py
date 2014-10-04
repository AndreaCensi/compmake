import time


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

if __name__ == '__main__':
    from compmake import Context
    context = Context()
    # A typical pattern: you want to try 
    # many combinations of parameters
    for param1 in [1,2,3]:
        for param2 in [10,11,12]:
            # Simply use "y = comp(f, x)" whenever
            # you would have used "y = f(x)".
            res1 = context.comp(func1, param1)
            # You can use return values as well.
            res2 = context.comp(func2, res1, param2)
            context.comp(draw, res2)

# At this point, nothing has been run yet.
# There are different options on how to run the computation,
# depending on how much fine-grained control you want,
# and if you want an interactive or batch experience.

# Now, a few options to run this:
# 1) Call this file using the compmake program:
#  $ python example.py
#  and then run "make" at the prompt.
import sys
if len(sys.argv) == 1:
    print('Presenting an interactive console')
    context.compmake_console()
    # 3) Or just run the computation in batch mode:
else:
    print('Running the computation in batch mode')
    cmd = " ".join(sys.argv[1:])
    context.batch_command(cmd)
