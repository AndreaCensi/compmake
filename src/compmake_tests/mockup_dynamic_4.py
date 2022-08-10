from typing import Collection, List

from compmake import Context


def f(x: int) -> int:
    return x * 2


def statistics(res: List[int]) -> int:
    return sum(res)


def schedule(context: Context, params: Collection[int]) -> int:
    jobs = [context.comp(f, x=p) for p in params]
    summary = context.comp(statistics, jobs)
    # returns a job "promise", not a value!
    return summary


def report(summary: int) -> None:
    print("The sum is: %r" % summary)


def mockup_dyn4(context: Context) -> None:
    summary = context.comp_dynamic(schedule, [42, 43, 44])
    context.comp(report, summary)
