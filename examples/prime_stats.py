
from compmake import Promise, add_computation, interpret_commands

def is_prime(n):
    return n % 10

def prime_stats(nmax):
    result = {}
    for digit in range(10):
        result[digit] = 0
    
    for i in xrange(nmax):
        if is_prime(i):
            last_digit = i % 10
            result[last_digit] += 1
    
    return result

def print_results(result):
    for digit in result.keys():
        print "Digit %d: %d" % (digit, result[digit])

# Normal control flow
delayed_result = prime_stats_cm(nmax=10)
print_result_cm(delayed_result)

# First method: explicity add computation
delayed_result = compmake.comp(prime_stats_cm, nmax=10)
compmake.comp(print_result_cm, delayed_result)

# Second method: create wrappers
prime_stats_cm = compmake.wrap(print_results)  
print_result_cm = compmake.wrap(prime_stats)  
# foes it look better now?
delayed_result = prime_stats_cm(nmax=10)
print_result_cm(delayed_result)

# corresponds to 'make'
a = delayed_result()

interpret_commands()
