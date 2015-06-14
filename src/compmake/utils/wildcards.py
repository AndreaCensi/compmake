import re

from ..exceptions import UserError


__all__ = [
    'wildcard_to_regexp',
    'expand_wildcard',
]


def wildcard_to_regexp(arg):
    """ Returns a regular expression from a shell wildcard expression. """
    return re.compile('\A' + arg.replace('*', '.*') + '\Z')


def expand_wildcard(wildcard, universe):
    """ Expands a wildcard expression against the given list.
        wildcard: string with '*'
        universe: list of strings
    """
    assert wildcard.find('*') > -1
    regexp = wildcard_to_regexp(wildcard)
    num_matches = 0
    for x in universe:
        if regexp.match(x):
            num_matches += 1
            yield x
    if num_matches == 0:
        msg = 'Could not find matches for pattern "%s".' % wildcard
        raise UserError(msg)
