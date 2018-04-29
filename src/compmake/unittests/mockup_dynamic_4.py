# -*- coding: utf-8 -*-
def f(x):
    return x * 2
def statistics(res): 
    return sum(res)
 
def schedule(context, params):
    jobs = [context.comp(f, x=p) for p in params]
    summary = context.comp(statistics, jobs)
    # returns a job "promise", not a value!
    return summary
 
def report(summary):
    print('The sum is: %r' % summary)
     
def mockup_dyn4(context):
    summary = context.comp_dynamic(schedule, [42, 43, 44])
    context.comp(report, summary)
