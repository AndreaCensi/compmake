from mycomputations import funcA, funcB, draw

if __name__ == '__main__':
    from compmake import Context
    context = Context()

    for param_a in [1, 2, 3]:
        for param_b in [10, 11, 12]: 
            prefix = 'a%s-b%s' % (param_a, param_b)
            context.comp_prefix(prefix)

            # use job_id to override default naming
            res1 = context.comp(funcA, param_a, 
                                job_id='preparing')
            res2 = context.comp(funcB, res1, param_b, 
                                job_id='computing')
            context.comp(draw, res2, 
                         job_id='drawing')

    context.compmake_console()

