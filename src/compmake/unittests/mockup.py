# -*- coding: utf-8 -*-
from compmake.context import Context
from contracts import contract
import sys


def f(*args):  # @UnusedVariable
    print('to-std-out')
    sys.stderr.write('to-std-err')
    return

def fails(*args):  # @UnusedVariable
    raise Exception('this function fails')


@contract(context=Context)
def mockup1(context):
    comp = context.comp
    return comp(f, comp(f), comp(f, comp(f)))


@contract(context=Context)
def mockup2(context):
    comp = context.comp

    comp(f, job_id='f1')
    comp(f, job_id='f2')
    res = comp(fails, job_id='fail1')
    comp(f, res, job_id='blocked')

    r5 = comp(f, job_id='f5')
    comp(f, r5, job_id='needs_redoing')

    comp(f, job_id='verylong' + 'a' * 40)

    context.batch_command('make')
    context.batch_command('clean f2')
    context.batch_command('clean f5')



@contract(context=Context)
def mockup2_nofail(context):
    comp = context.comp

    comp(f, job_id='f1')
    comp(f, job_id='f2')

    r5 = comp(f, job_id='f5')
    comp(f, r5, job_id='needs_redoing')

    comp(f, job_id='verylong' + 'a' * 40)

    context.batch_command('make')
    context.batch_command('clean f2')
    context.batch_command('clean f5')


def mockup_recursive_5(context):
    recursive(context, 5)

def recursive(context, v):
    if v == 0:
        print('finally!')
        return

    context.comp_dynamic(recursive, v - 1, job_id='r%d' % v)
