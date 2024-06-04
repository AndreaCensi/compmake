import sys
from io import StringIO
from typing import Callable

from .coloredterm import termcolor_colored
from .strings_with_escapes import pad_to_screen

RESET = "\033[0m"  # XXX

__all__ = [
    "OutputCapture",
]


class LineSplitter:
    """A simple utility to split an incoming sequence of chars
    in lines. Push characters using append_chars() and
    get the completed lines using lines()."""

    def __init__(self):
        self.current = ""
        self.current_lines = []

    def append_chars(self, s: str):
        assert isinstance(s, str), s
        for char in s:
            if char == "\n":
                self.current_lines.append(self.current)
                self.current = ""
            else:
                self.current += char

    def lines(self) -> list[str]:
        """Returns a list of line; empties the buffer"""
        l = list(self.current_lines)
        self.current_lines = []
        return l


class StreamCapture:
    def __init__(self, transform=None, dest=None, after_lines=None):
        """dest has write() and flush()"""
        self.buffer = StringIO()
        self.dest = dest
        self.transform = transform
        self.line_splitter = LineSplitter()
        self.after_lines = after_lines

    def write(self, s: str):
        assert isinstance(s, str), s
        self.buffer.write(s)
        self.line_splitter.append_chars(s)
        lines = self.line_splitter.lines()

        if self.dest:
            # XXX: this has a problem with colorized things over multiple lines
            for line in lines:
                if self.transform:
                    line = self.transform(line)
                self.dest.write("%s\n" % line)

            # self.dest.write(self.transform(s))
            self.dest.flush()

        if self.after_lines is not None:
            self.after_lines(lines)

    def get_value_text_type(self):
        b = self.buffer.getvalue()

        return b

    def flush(self) -> None:
        pass


# TODO: this thing does not work with logging enabled
class OutputCapture:
    def __init__(
        self,
        prefix: str,
        echo_stdout: bool,
        echo_stderr: bool,
        publish_stdout: Callable[[list[str]], None],
        publish_stderr: Callable[[list[str]], None],
    ):
        self.prefix = prefix
        sys.stderr.write(f"OutputCapture({self.prefix!r})\n")
        self.old_stdout = sys.stdout
        self.old_stderr = sys.stderr

        # t1 = lambda s: '%s|%s' % (prefix, colored(s, 'cyan', attrs=['dark']))

        # FIXME: perhaps we should use compmake_colored
        t1 = lambda s: "%s|%s" % (termcolor_colored(prefix, "white", attrs=["dark"]), s)
        t2 = lambda s: RESET + pad_to_screen(t1(s))
        dest = {True: sys.stdout, False: None}[echo_stdout]
        self.stdout_replacement = StreamCapture(transform=t2, dest=dest, after_lines=publish_stdout)
        sys.stdout = self.stdout_replacement

        # t3 = lambda s: '%s|%s' % (prefix, colored(s, 'red', attrs=['dark']))
        t3 = lambda s: "%s|%s" % (termcolor_colored(prefix, "red", attrs=["dark"]), s)
        t4 = lambda s: RESET + pad_to_screen(t3(s))
        dest = {True: sys.stderr, False: None}[echo_stderr]
        self.stderr_replacement = StreamCapture(transform=t4, dest=dest, after_lines=publish_stderr)
        sys.stderr = self.stderr_replacement

    def deactivate(self) -> None:
        sys.stdout = self.old_stdout
        sys.stderr = self.old_stderr
        sys.stderr.write(f"OutputCapture({self.prefix!r}): deactivatd \n")

    def get_logged_stdout(self) -> str:
        return self.stdout_replacement.get_value_text_type()  # buffer.getvalue()

    def get_logged_stderr(self) -> str:
        return self.stderr_replacement.get_value_text_type()  # buffer.getvalue()
