
class HTML_status_writer:
    
    def update(self):
        pass
    
    def compmake_event(self, event, **kwargs):
        pass
    
    
    
    
handler = HTML_status_writer()
register_event_handler(handler.compmake_event)
