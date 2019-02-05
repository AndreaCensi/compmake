# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import random

failure_prob = 0.3

def fail_randomly():
    if random.random() < failure_prob:
        raise Exception('Unlucky job failed randomly')

def first(children=[]):
    fail_randomly()


def second(children=[]):
    fail_randomly()


def third(children=[]):
    fail_randomly()
