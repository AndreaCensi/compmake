
from compmake import comp, progress
import time

def mylongfunction():

    N = 4
    
    for i in range(N):
        progress('Task A', (i,N))
        time.sleep(1)
        
    for i in range(N):
        progress('Task B', (i,N))
        time.sleep(1)
        
            
comp(mylongfunction)
