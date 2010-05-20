
handlers = {}

def register_handler(event_name, handler):
    if not event_name in handlers:
        handlers[event_name] = []
        
    handlers[event_name].append(handler)
    
def broadcast_event(event_name, **kwargs):
    pass
