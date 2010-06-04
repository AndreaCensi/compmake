from compmake import comp, progress
import time

def mylongfunction():
    
    directories = ['a', 'b', 'c', 'd', 'e']
    n = len(directories)
    for i, dir in enumerate(directories):
        progress('Processing directories', (i, n), 'Directory %s' % dir)
        
        N = 10
        for k in range(N):
            progress('Processing files', (k, N), 'file #%d' % k)
            
            time.sleep(1)
            
            
comp(mylongfunction)
