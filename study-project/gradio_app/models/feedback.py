import os
import json
import time
import httpx
from datetime import datetime

import gradio as gr
from gradio_app.config import settings
from gradio_app.utils.logger import log_print

class FeedbackModel:
    
    def __init__(self):
        self.feedback_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "feedback"
        )
        os.makedirs(self.feedback_dir, exist_ok=True)
        log_print("FeedbackModel initialized")
    
    #-------------------------------------------------------------------------
    # FEEDBACK COLLECTION AND STORAGE
    #-------------------------------------------------------------------------
    
    async def save_feedback(self, scenario_id, condition, session, *slider_values):
        try:
            if scenario_id == "completed" or (session and session.study_completed):
                log_print(f"Study already completed for session {session.session_id if session else 'unknown'}. Skipping feedback.")
                return True
                
            if not session or not session.study_token:
                log_print("No valid session or study token provided for feedback")
                raise gr.Error("Session oder Token fehlt. Bitte versuche es erneut oder lade die Seite neu.")
            
            user_id = session.study_token
            log_print(f"Saving feedback for session {session.session_id} with token: {user_id}")

            feedback_data = self._create_feedback_data(scenario_id, condition, slider_values, session)
            file_path = self._save_to_file(feedback_data, user_id)
            log_print(f"Feedback saved to {file_path}")
            
            session.feedback_submitted = True
            
            from gradio_app.models.scenario import scenario_manager
            task_distributor = scenario_manager.task_distributor
            
            if task_distributor:
                task_distributor.mark_scenario_completed(
                    session.study_token, 
                    session.current_scenario_id, 
                    session.current_condition
                )
            
            time.sleep(settings.Feedback.FEEDBACK_CONFIRMATION_DELAY)
            
            gr.Info("Feedback erfolgreich gespeichert!")
            
            return True
            
        except gr.Error as e:
            raise
        except Exception as e:
            log_print(f"Error saving feedback: {str(e)}")
            raise gr.Error("Ein Fehler ist aufgetreten beim Speichern des Feedbacks.")
    

    def _create_feedback_data(self, scenario_id, condition, slider_values, session=None):
        ratings = {}
        for i, value in enumerate(slider_values):
            if i < len(settings.Feedback.SLIDER_CATEGORIES):
                category = settings.Feedback.SLIDER_CATEGORIES[i]
                ratings[category] = value
        
        feedback_data = {
            "timestamp": datetime.now().isoformat(),
            "scenario_id": scenario_id,
            "condition": condition,
            "ratings": ratings
        }
        
        if session and session.token_rate_tokens_per_second is not None:
            try:
                token_rate = float(session.token_rate_tokens_per_second)
                feedback_data["tokens_per_second"] = token_rate
                log_print(f"Added token rate data ({token_rate:.2f} tokens/sec) to feedback")
            except (ValueError, TypeError) as e:
                log_print(f"Warning: Failed to add token rate to feedback - invalid value: {session.token_rate_tokens_per_second}. Error: {str(e)}")
        else:
            log_print("No token rate data available for this feedback submission")
        
        if session and session.response_delay is not None:
            try:
                response_delay = float(session.response_delay)
                feedback_data["response_delay_seconds"] = response_delay
                log_print(f"Added response delay data ({response_delay:.2f} seconds) to feedback")
            except (ValueError, TypeError) as e:
                log_print(f"Warning: Failed to add response delay to feedback - invalid value: {session.response_delay}. Error: {str(e)}")
        else:
            log_print("No response delay data available for this feedback submission")
            
        return feedback_data
    
    def generate_user_directory(self, user_id):
        user_dir = os.path.join(self.feedback_dir, user_id)
        os.makedirs(user_dir, exist_ok=True)
        return user_dir
    
    def _save_to_file(self, feedback_data, user_id):
        timestamp = datetime.now().strftime("%d%m%Y_%H%M%S")
        user_dir = self.generate_user_directory(user_id)
        filename = f"feedback_{user_id}_{timestamp}.json"
        file_path = os.path.join(user_dir, filename)
        
        with open(file_path, "w") as f:
            json.dump(feedback_data, f, indent=2)
            
        return file_path
    
    #-------------------------------------------------------------------------
    # UI INTERACTIONS
    #-------------------------------------------------------------------------
    
    # Shows the feedback UI after the response
    def show_feedback(self, chat_history):
        gr.Info("Bitte geben Sie Ihr Feedback zur Antwort des KI-Systems!")
        return chat_history, gr.update(interactive=True), gr.update(visible=True)

# Create singleton instance
feedback_model = FeedbackModel() 