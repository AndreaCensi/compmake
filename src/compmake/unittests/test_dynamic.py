from tempfile import mkdtemp

from compmake.context import Context
from compmake.storage.filesystem import StorageFilesystem


def cases():
    print('returned cases')
    return [1, 2, 3]

def actual_tst(value):
    print('actual_tst(value)')
    return value * 2

def generate_tsts(context, values):
    res = []
    for v in values:
        res.append(context.comp(actual_tst, v))
    return context.comp(finish, res)

def finish(values):
    return sum(values)

def test_dynamic1():
    root = mkdtemp()
    root = 'test_dynamic1'
    print('using %s' % root)
    db = StorageFilesystem(root)
    cc = Context(db=db)

    values = cc.comp(cases, job_id='main')
    cc.comp_dynamic(generate_tsts, values)

    res = cc.interpret_commands_wrap('make')
    print('result: %s' % res)

    res = cc.interpret_commands_wrap('make')


    print('result: %s' % res)
