import sys
from compmake.utils.visualization import colored


class StreamCapture:
    def __init__(self, transform=None, dest=None):
        self.buffer = []
        self.dest = dest
        self.transform = transform
    def write(self, s):
        self.buffer.append(s)
        if self.transform:
            s = self.transform(s)
        if self.dest:
            self.dest.write(s)
        

class OutputCapture:
    
    def __init__(self, prefix):
        self.old_stdout = sys.stdout
        self.old_stderr = sys.stderr
        t = lambda s: '%s| %s' % (prefix, colored(s, attrs=['dark'])) 
        self.stdout_replacement = StreamCapture(transform=t, dest=sys.stdout)
        sys.stdout = self.stdout_replacement
        
        t = lambda s: '%s| %s' % (prefix, colored(s, 'red', attrs=['dark'])) 
        self.stderr_replacement = StreamCapture(transform=t, dest=sys.stderr)
        sys.stderr = self.stderr_replacement
        
    def deactivate(self):
        sys.stdout = self.old_stdout
        sys.stderr = self.old_stderr
        
