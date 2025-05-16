from zuper_commons.types import ZValueError

from .strings_with_escapes import get_length_on_screen
from .strings_with_escapes import pad_to_screen_length

__all__ = [
    "TableFormatter",
]


class TableFormatter:
    def __init__(self, sep: str = "|"):
        self.rows = []
        self.cur_row = None
        self.sep = sep

        self.padleft = lambda s, l: pad_to_screen_length(s, l)
        self.strlen = get_length_on_screen

    def row_complete(self, cols: list[str]) -> None:
        if self.cur_row is not None:
            self._push_row()
        self.rows.append(cols)

    def row(self):
        if self.cur_row is not None:
            self._push_row()

        self.cur_row = []

    def _push_row(self):
        if self.rows:
            ncols = len(self.rows[0])
            the_row = list(self.cur_row)

            if ncols < len(the_row):
                msg = "Invalid row"
                raise ZValueError(msg, first_row=self.rows[0], cur_row=the_row)

            while len(the_row) < ncols:
                the_row.append("")

        else:
            the_row = self.cur_row

        self.rows.append(the_row)

    def cell(self, s):
        if self.cur_row is None:
            raise ValueError("Call row() before cell().")
        self.cur_row.append(str(s))

    def done(self):
        if self.cur_row is None:
            raise ValueError("Call row() before done().")
        self._push_row()

    def _get_cols(self):
        ncols = len(self.rows[0])
        cols = [list() for _ in range(ncols)]
        for j in range(ncols):
            for r in self.rows:
                cols[j].append(r[j])
        return cols

    def get_lines(self):
        cols = self._get_cols()
        # width of each cols
        wcol = [max(self.strlen(s) for s in col) for col in cols]
        for r in self.rows:
            r = self._get_row_formatted(r, wcol)
            yield r

    def get_lines_multi(self, linewidth, sep="   "):
        """Gets lines, perhaps multiples on a line"""

        # Get all lines
        lines = self.get_lines()
        # Find maximum length of line
        maxlen = max(map(self.strlen, lines))
        #         print('-' * maxlen)
        ncols = 1
        while True:
            l = ncols * maxlen + (ncols - 1) * self.strlen(sep)
            fits = l < linewidth
            #             print(ncols, '->', l)
            if not fits:
                break
            ncols += 1
        ncols -= 1
        ncols = max(1, ncols)

        for mates in groups_match(self.get_lines(), ncols):
            s = sep.join(mates)
            #             print('mates = %r' % mates)
            # FIXME: this raises an error --- (137, 135)
            # assert self.strlen(s) <= linewidth, (self.strlen(s), linewidth)
            if self.strlen(s) > linewidth:
                # raise ValueError()
                pass
            yield s

    def _get_row_formatted(self, row, wcol):
        ss = []
        for j, cell in enumerate(row):
            if wcol[j] > 0:
                entry = self.padleft(cell, wcol[j])
                ss.append(entry)
        return self.sep.join(ss).rstrip()


def groups_match(it, groupsize) -> list:
    content = list(it)
    gs = list(groups(content, groupsize))
    ngroups = len(gs)

    nrows = ngroups
    ncols = groupsize
    table = []
    for _ in range(nrows):
        row = []
        for _ in range(ncols):
            row.append(None)
        table.append(row)

    for i, x in enumerate(content):
        row = i % nrows
        col = int((i - row) / nrows)
        assert 0 <= col < ncols
        assert 0 <= row < nrows
        table[row][col] = x

    for row in table:
        row = list(filter(lambda _: _ is not None, row))
        yield row


def groups(it, groupsize):
    cur = []
    for x in it:
        cur.append(x)
        if len(cur) == groupsize:
            yield cur
            cur = []
    if cur:
        yield cur
