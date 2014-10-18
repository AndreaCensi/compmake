def funcA(param1): 
    print('funcA(%r)' % param1)
    return param1 * 10
    
def funcB(param1, param2): #@UnusedVariable
    print('funcB(%r, %r)' % (param1, param2))
    return param1 + param2
    
def draw(result): 
    print('draw(%r)' % result)

    
