import sys, re
from compmake.utils.visualization import colored, getTerminalSize,\
    get_screen_columns
from StringIO import StringIO

class LineSplitter:
    ''' A simple utility to split an incoming sequence of chars
        in lines. Push characters using append_chars() and 
        get the completed lines using lines(). '''
        
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
                self.dest.write("%s\n" % line)
            self.dest.flush()
        
    def flush(self):
        pass

def remove_escapes(s):
    escape = re.compile('\x1b\[..?m')
    return escape.sub("",s)

def pad_to_screen(s):
    ''' Pads a string to the terminal size.
    The string length is computed after removing shell 
    escape sequences. '''
    
    current_size = len(remove_escapes(s))
    desired_size = get_screen_columns() - 1 
    
    pad_char = " "
    # pad_char = "_" # useful for debugging
    
    if current_size < desired_size:
        s += pad_char * (desired_size - current_size)
        
    return s

class OutputCapture:
    
    def __init__(self, prefix, echo_stdout=True, echo_stderr=True):
        self.old_stdout = sys.stdout
        self.old_stderr = sys.stderr
        t1 = lambda s: '%s| %s' % (prefix, colored(s, 'cyan', attrs=['dark']))
        t2 = lambda s: pad_to_screen(t1(s))
        dest = {True: sys.stdout, False: None}[echo_stdout]     
        self.stdout_replacement = StreamCapture(transform=t2, dest=dest)
        sys.stdout = self.stdout_replacement
        
        t3 = lambda s: '%s| %s' % (prefix, colored(s, 'red', attrs=['dark']))
        t4 = lambda s: pad_to_screen(t3(s))
        dest = {True: sys.stderr, False: None}[echo_stderr]      
        self.stderr_replacement = StreamCapture(transform=t4, dest=dest)
        sys.stderr = self.stderr_replacement
        
    def deactivate(self):
        sys.stdout = self.old_stdout
        sys.stderr = self.old_stderr
        
