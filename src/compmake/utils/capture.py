from . import pad_to_screen, termcolor_colored as colored
from StringIO import StringIO
import sys

RESET = '\033[0m'  # XXX


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
    def __init__(self, transform=None, dest=None, after_lines=None):
        ''' dest has write() and flush() '''
        self.buffer = StringIO()
        self.dest = dest
        self.transform = transform
        self.line_splitter = LineSplitter()
        self.after_lines = after_lines

    def write(self, s):
        self.buffer.write(s)
        self.line_splitter.append_chars(s)
        lines = self.line_splitter.lines()

        if self.dest:
            # XXX: this has a problem with colorized things over multiple lines
            for line in lines:
                if self.transform:
                    line = self.transform(line)
                self.dest.write("%s\n" % line)

#            self.dest.write(self.transform(s))
            self.dest.flush()

        if self.after_lines is not None:
            self.after_lines(lines)

    def flush(self):
        pass


# TODO: this thing does not work with logging enabled
class OutputCapture:

    def __init__(self, prefix, echo_stdout=True, echo_stderr=True):
        self.old_stdout = sys.stdout
        self.old_stderr = sys.stderr

        from ..events import publish

        def publish_stdout(lines):  # @UnusedVariable
            publish('job-stdout', job_id=prefix, lines=lines)

        def publish_stderr(lines):  # @UnusedVariable
            publish('job-stderr', job_id=prefix, lines=lines)

        #t1 = lambda s: '%s|%s' % (prefix, colored(s, 'cyan', attrs=['dark']))
        t1 = lambda s: '%s|%s' % (colored(prefix, attrs=['dark']), s)
        t2 = lambda s: RESET + pad_to_screen(t1(s))
        dest = {True: sys.stdout, False: None}[echo_stdout]
        self.stdout_replacement = StreamCapture(transform=t2, dest=dest,
                                                after_lines=publish_stdout)
        sys.stdout = self.stdout_replacement

        #t3 = lambda s: '%s|%s' % (prefix, colored(s, 'red', attrs=['dark']))
        t3 = lambda s: '%s|%s' % (colored(prefix, 'red', attrs=['dark']), s)
        t4 = lambda s: RESET + pad_to_screen(t3(s))
        dest = {True: sys.stderr, False: None}[echo_stderr]
        self.stderr_replacement = StreamCapture(transform=t4, dest=dest,
                                                after_lines=publish_stderr)
        sys.stderr = self.stderr_replacement

    def deactivate(self):
        sys.stdout = self.old_stdout
        sys.stderr = self.old_stderr
