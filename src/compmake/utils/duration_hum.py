# -*- coding: utf-8 -*-
import math

__all__ = [
    # 'duration_human',
    'duration_compact',
]
#
# def duration_human(seconds):
# ''' Code modified from
#     http://darklaunch.com/2009/10/06
#     /python-time-duration-human-friendly-timestamp
#     '''
#     seconds = int(math.ceil(seconds))
#     minutes, seconds = divmod(seconds, 60)
#     hours, minutes = divmod(minutes, 60)
#     days, hours = divmod(hours, 24)
#     years, days = divmod(days, 365.242199)
#
#     minutes = int(minutes)
#     hours = int(hours)
#     days = int(days)
#     years = int(years)
#
#     duration = []
#     if years > 0:
#         duration.append('%d year' % years + 's' * (years != 1))
#     else:
#         if days > 0:
#             duration.append('%d day' % days + 's' * (days != 1))
#         if (days < 3) and (years == 0):
#             if hours > 0:
#                 duration.append('%d hour' % hours + 's' * (hours != 1))
#             if (hours < 3) and (days == 0):
#                 if minutes > 0:
#                     duration.append('%d min' % minutes +
#                                      's' * (minutes != 1))
#                 if (minutes < 3) and (hours == 0):
#                     if seconds > 0:
#                         duration.append('%d sec' % seconds +
#                                          's' * (seconds != 1))
#
#     return ' '.join(duration)


def duration_compact_ms(s):
    ms = 1000 * s
    return '%d ms' % ms


def duration_compact(seconds):
    if seconds < 1:
        return duration_compact_ms(seconds)
    seconds = int(math.ceil(seconds))
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    years, days = divmod(days, 365.242199)

    minutes = int(minutes)
    hours = int(hours)
    days = int(days)
    years = int(years)

    duration = []
    if years > 0:
        duration.append('%dy' % years)
    else:
        if days > 0:
            duration.append('%dd' % days)
        if (days < 3) and (years == 0):
            if hours > 0:
                duration.append('%dh' % hours)
            if (hours < 3) and (days == 0):
                if minutes > 0:
                    duration.append('%dm' % minutes)
                if (minutes < 3) and (hours == 0):
                    if seconds > 0:
                        duration.append('%ds' % seconds)

    return ' '.join(duration)

