import sys
from compmake.utils.visualization import colored
from StringIO import StringIO

class LineSplitter:
    def __init__(self):
        self.current = ''
        self.current_lines = []
        
    def append_chars(self, s):
        # TODO: make this faster
        s = str(s)
        for char in s:
            if char == '\n':
                self.current_lines.append(self.current)
                self.current = ''
            else:
                self.current += char
            
            
    def lines(self):
        ''' Returns a list of line; empties the buffer '''
        l = list(self.current_lines)
        self.current_lines = []
        return l


class StreamCapture:
    def __init__(self, transform=None, dest=None):
        ''' dest has write() and flush() '''
        self.buffer = StringIO()
        self.dest = dest
        self.transform = transform
        self.line_splitter = LineSplitter()
        
    def write(self, s):
        self.buffer.write(s)
        if self.dest:
            self.line_splitter.append_chars(s)
            for line in self.line_splitter.lines():
                if self.transform:
                    line = self.transform(line)       
                self.dest.write(line)
                self.dest.write('\n')
            self.dest.flush()
        
    def flush(self):
        pass

class OutputCapture:
    
    def __init__(self, prefix, echo_stdout=True, echo_stderr=True):
        self.old_stdout = sys.stdout
        self.old_stderr = sys.stderr
        t = lambda s: '%s| %s' % (prefix, colored(s, 'cyan', attrs=['dark']))
        dest = {True: sys.stdout, False: None}[echo_stdout]     
        self.stdout_replacement = StreamCapture(transform=t, dest=dest)
        sys.stdout = self.stdout_replacement
        
        t = lambda s: '%s| %s' % (prefix, colored(s, 'red', attrs=['dark']))
        dest = {True: sys.stderr, False: None}[echo_stderr]      
        self.stderr_replacement = StreamCapture(transform=t, dest=dest)
        sys.stderr = self.stderr_replacement
        
    def deactivate(self):
        sys.stdout = self.old_stdout
        sys.stderr = self.old_stderr
        
