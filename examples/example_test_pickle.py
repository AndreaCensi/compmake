def f1():
    """ Docs of this function. """
    pass


import sys

from compmake.utils import safe_pickle_dump

if __name__ == "__main__":
    # module = sys.modules['__main__']
    print(sys.modules["__main__"])
    filename = "f1.pickle"
    safe_pickle_dump(f1, filename)


# if __name__ == '__main__':
#     import compmake
#     c = compmake.ContextImp()
#     c.comp(f1)
#      await c.batch_command(sti,'make')
