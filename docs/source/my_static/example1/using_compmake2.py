from mycomputations import funcA, funcB, draw

if __name__ == '__main__':
    from compmake import Context
    context = Context()

    for param_a in [1, 2, 3]:
        for param_b in [10, 11, 12]:
            # Add a prefix to the job ids for easy reference 
            prefix = 'a%s-b%s' % (param_a, param_b)
            context.comp_prefix(prefix)

            res1 = context.comp(funcA, param_a)
            res2 = context.comp(funcB, res1, param_b)
            context.comp(draw, res2)

    context.compmake_console()

