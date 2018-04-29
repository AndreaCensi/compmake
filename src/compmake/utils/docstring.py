# -*- coding: utf-8 -*-
import sys

# Code copied from PEP-0257

__all__ = ['docstring_trim', 'docstring_components']


def docstring_trim(docstring):
    if not docstring:
        return ''
    # Convert tabs to spaces (following the normal Python rules)
    # and split into a list of lines:
    lines = docstring.expandtabs().splitlines()
    # Determine minimum indentation (first line doesn't count):
    indent = sys.maxint
    for line in lines[1:]:
        stripped = line.lstrip()
        if stripped:
            indent = min(indent, len(line) - len(stripped))
    # Remove indentation (first line is special):
    trimmed = [lines[0].strip()]
    if indent < sys.maxint:
        for line in lines[1:]:
            trimmed.append(line[indent:].rstrip())
    # Strip off trailing and leading blank lines:
    while trimmed and not trimmed[-1]:
        trimmed.pop()
    while trimmed and not trimmed[0]:
        trimmed.pop(0)
    # Return a single string:
    return '\n'.join(trimmed)


def docstring_components(docstring):
    """ 
    
        Removes leading whitespace and returns a dict
        with fields "first" and "rest".
        
        This is the rest.
    
    """

    # first, remove whitespace
    docstring = docstring_trim(docstring)
    # split in newlines
    lines = docstring.split('\n')
    # trim each one
    lines = map(lambda x: x.strip(), lines)
    # remove initial empty ones
    while lines and lines[0] == '':
        lines.pop(0)
    first = []
    while lines and lines[0] != '':
        first.append(lines.pop(0))

    # remove separation
    while lines and lines[0] == '':
        lines.pop(0)
    rest = lines

    res = {'first': ' '.join(first),
           'rest': '\n'.join(rest)}
    # remove newlines here
    return res


def docstring_components_test():
    res = docstring_components(docstring_components.__doc__)
    print(res)

    assert res['first'] == 'Removes leading whitespace and returns a dict ' \
                           'with fields "first" and "rest".'
    assert res['rest'] == 'This is the rest.'
