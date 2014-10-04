from mycomputations import func1, func2, draw

if __name__ == '__main__':
    from compmake import Context
    context = Context()

    for param1 in [1, 2, 3]:
        for param2 in [10, 11, 12]: 
            context.comp_prefix('p1=%s-p2=%s' % (param1,param2))
            
            # use job_id to override default naming
            res1 = context.comp(func1, param1, job_id='preparing')
            res2 = context.comp(func2, res1, param2, job_id='computing')
            context.comp(draw, res2, job_id='drawing')

    context.compmake_console()

