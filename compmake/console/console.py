import readline
from compmake.structures import Computation
from compmake.visualization import user_error 
from compmake.ui_commands_helpers import find_commands
#    
#def tab_completion(text, state):
#    print '"%s"' % text
#    space_at_the_end = text.endswith(' ')
#    text = text.strip()
#    
#    words = text.split() 
#    if len(words) == 1 and space_at_the_end:
#        if words[0] == 'help':
#            # complete with command
#            available = find_commands().keys()
#        else:
#            # complete with task
#            available = Computation.id2computations.keys()
#    else:
#        # complete with task 
#        available = Computation.id2computations.keys()
#    
#    last_word = words[1]
#    matches = sorted(x for x in available if x.startswith(text))
#    try:
#        response = matches[state]
#    except IndexError:
#        response = None
#    return response
#    

def tab_completion2(text, state):
    available = find_commands().keys()
    available.extend(Computation.id2computations.keys())
    matches = sorted(x for x in available if x.startswith(text))
    try:
        response = matches[state]
    except IndexError:
        response = None
    return response

def compmake_console():
    readline.set_completer(tab_completion2)
    readline.parse_and_bind('tab: complete')
    try:
        while True:
            line = raw_input('@: ')
            yield line
    except Exception as e:
        # TODO
        user_error(e)
    

