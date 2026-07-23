import uuid
import gradio as gr
from gradio_app.utils.logger import log_print

class AuthModel:
    def __init__(self):
        log_print("AuthModel initialized")
    
    #-------------------------------------------------------------------------
    # TOKEN VALIDATION
    #-------------------------------------------------------------------------
    
    def validate_token(self, token, session):
        log_print(f"Validating token: {token}")
        
        session.update_activity()
        
        if not token:
            log_print("Token validation failed: Token empty")
            gr.Warning("Token Validierung fehlgeschlagen: Token leer")
            return gr.update(visible=True), gr.update(visible=False), session
        elif len(token) < 10:
            log_print("Token validation failed: Token too short")
            gr.Warning("Token Validierung fehlgeschlagen: Token zu kurz")
            return gr.update(visible=True), gr.update(visible=False), session
        
        try:
            uuid.UUID(token)
        except ValueError:
            log_print("Token validation failed: Invalid UUID")
            gr.Warning("Token Validierung fehlgeschlagen: Ungültige UUID")
            return gr.update(visible=True), gr.update(visible=False), session
        
        session.set_authentication(token)
        
        log_print(f"Token validated successfully: {token} for session {session.session_id}")
        
        gr.Info("Token erfolgreich validiert. Willkommen zur Studie!")
        
        # Hide auth screen and show main interface
        return gr.update(visible=False), gr.update(visible=True), session

# Create singleton instance
auth_model = AuthModel() 