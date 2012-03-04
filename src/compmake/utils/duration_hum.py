import math


def duration_human(seconds):
    ''' Code modified from 
    http://darklaunch.com/2009/10/06
    /python-time-duration-human-friendly-timestamp
    '''
    seconds = long(math.ceil(seconds))
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    years, days = divmod(days, 365.242199)

    minutes = long(minutes)
    hours = long(hours)
    days = long(days)
    years = long(years)

    duration = []
    if years > 0:
        duration.append('%d year' % years + 's' * (years != 1))
    else:
        if days > 0:
            duration.append('%d day' % days + 's' * (days != 1))
        if (days < 3) and (years == 0):
            if hours > 0:
                duration.append('%d hour' % hours + 's' * (hours != 1))
            if (hours < 3) and (days == 0):
                if minutes > 0:
                    duration.append('%d minute' % minutes +
                                     's' * (minutes != 1))
                if (minutes < 3) and (hours == 0):
                    if seconds > 0:
                        duration.append('%d second' % seconds +
                                         's' * (seconds != 1))

    return ' '.join(duration)


