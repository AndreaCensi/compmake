import sys
from math import ceil

# TODO: generalize with curses
def red_color(string):
    return "\033[0;31m%s\033[m" % str(string)

def purple_color(string):
    return "\033[0;31m%s\033[m" % str(string)

def green_color(string):
    return "\033[0;36m%s\033[m" % str(string)

def normal_color(string):
    return  str(string)
    

def warning(string):
    write_message(string, formatting=red_color)
    
def error(string):
    write_message(string, formatting=red_color)
    
def user_error(string):
    write_message(string, formatting=purple_color)

def info(string):
    write_message(string, formatting=green_color)

def debug(string):
    write_message(string, formatting=normal_color)

def write_message(string, formatting):
    string = str(string)
    sys.stdout.flush()
    lines = string.split('\n')
    if len(lines) == 1:
        sys.stderr.write(formatting(lines[0]) + '\n')
    else:
        for i, l in enumerate(lines):
            if i == 1: 
                l = '- ' + l
            else:
                l = '  ' + l
            
            sys.stderr.write(formatting(l) + '\n')    
    
    sys.stderr.flush()
    

    
def duration_human(seconds):
    ''' Code modified from 
    http://darklaunch.com/2009/10/06
    /python-time-duration-human-friendly-timestamp
    '''
    seconds = long(ceil(seconds))
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


