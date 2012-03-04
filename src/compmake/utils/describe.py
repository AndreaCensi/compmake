import sys


inPy2 = sys.version_info[0] == 2
if inPy2:
    from types import ClassType


def clipped_repr(x, clip):
    s = "{0!r}".format(x)
    if len(s) > clip:
        clip_tag = '... [clip]'
        cut = clip - len(clip_tag)
        s = "%s%s" % (s[:cut], clip_tag)
    return s

# TODO: add checks for these functions


def remove_newlines(s):
    return s.replace('\n', ' ')


def describe_type(x):
    ''' Returns a friendly description of the type of x. '''
    if inPy2 and isinstance(x, ClassType):
        class_name = '(old-style class) %s' % x
    else:
        if hasattr(x, '__class__'):
            class_name = '%s' % x.__class__.__name__
        else:
            # for extension classes (spmatrix)
            class_name = str(type(x))

    return class_name


def describe_value(x, clip=50):
    ''' Describes an object, for use in the error messages. '''
    if hasattr(x, 'shape') and hasattr(x, 'dtype'):
        shape_desc = 'x'.join(str(i) for i in x.shape)
        desc = 'array[%s](%s) ' % (shape_desc, x.dtype)
        final = desc + clipped_repr(x, clip - len(desc))
        return remove_newlines(final)
    else:
        class_name = describe_type(x)
        desc = 'Instance of %s: ' % class_name
        final = desc + clipped_repr(x, clip - len(desc))
        return remove_newlines(final)


