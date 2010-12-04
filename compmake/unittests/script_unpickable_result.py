from compmake import comp

def f1():
    return lambda x: None #@UnusedVariable


comp(f1)
