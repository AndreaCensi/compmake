import sys
from compmake.utils.visualization import colored
from StringIO import StringIO


class StreamCapture:
    def __init__(self, transform=None, dest=None):
        self.buffer = StringIO()
        self.dest = dest
        self.transform = transform
        
    def write(self, s):
        self.buffer.write(s)
        if self.transform:
            s = self.transform(s)
        if self.dest:
            self.dest.write(s)
        

class OutputCapture:
    
    def __init__(self, prefix, echo=True):
        self.old_stdout = sys.stdout
        self.old_stderr = sys.stderr
        t = lambda s: '%s| %s' % (prefix, colored(s, attrs=['dark']))
        dest = {True: sys.stdout, False: None}[echo]     
        self.stdout_replacement = StreamCapture(transform=t, dest=dest)
        sys.stdout = self.stdout_replacement
        
        t = lambda s: '%s| %s' % (prefix, colored(s, 'red', attrs=['dark']))
        dest = {True: sys.stderr, False: None}[echo]      
        self.stderr_replacement = StreamCapture(transform=t, dest=dest)
        sys.stderr = self.stderr_replacement
        
    def deactivate(self):
        sys.stdout = self.old_stdout
        sys.stderr = self.old_stderr
        
