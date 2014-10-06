from mycomputations import funcA, funcB, draw

if __name__ == '__main__':
    from compmake import Context
    context = Context()

    for param1 in [1, 2, 3]:
        for param2 in [10, 11, 12]:
            # Add a prefix to the job ids
            # for easy reference 
            context.comp_prefix('p1=%s-p2=%s' % (param1,param2))
                    
            res1 = context.comp(funcA, param1)
            res2 = context.comp(funcB, res1, param2)
            context.comp(draw, res2)

    context.compmake_console()

