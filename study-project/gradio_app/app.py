import os
import sys
import traceback
import uuid
from datetime import datetime, timedelta
import gradio as gr

# Add the parent directory to the Python path for absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from gradio_app.config import settings
from gradio_app.utils.logger import log_print
from gradio_app.utils.assets import load_asset
from gradio_app.models.scenario import scenario_manager
from gradio_app.models.chat import chat_model
from gradio_app.models.feedback import feedback_model
from gradio_app.models.auth import auth_model
from gradio_app.ui.components import UIComponents


class UserSession:
    
    def __init__(self, session_id=None):
        self.session_id = session_id or str(uuid.uuid4())
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        
        # User authentication
        self.study_token = None
        self.is_authenticated = False
        
        # Scenario state
        self.current_scenario_id = None
        self.current_condition = None
        self.current_scenario_data = None
        self.scenario_history = []
        self.response_delay = settings.Chat.FALLBACK_DELAY
        
        # Chat state
        self.chat_history = []
        
        # Feedback state
        self.feedback_submitted = False
        self.study_completed = False
        
        # Token rate data
        self.token_rate_tokens_per_second = None
        
        # Session timeout in minutes (default: 60 minutes)
        self.timeout_minutes = 60
        
        log_print(f"Created new user session: {self.session_id}")
    
    def update_activity(self):
        self.last_activity = datetime.now()
    
    def is_timed_out(self):
        time_since_activity = datetime.now() - self.last_activity
        timeout_threshold = timedelta(minutes=self.timeout_minutes)
        is_timeout = time_since_activity > timeout_threshold
        
        if is_timeout:
            log_print(f"Session {self.session_id} has timed out after {time_since_activity}")
        
        return is_timeout
    
    def set_authentication(self, study_token):
        self.study_token = study_token
        self.is_authenticated = True
        log_print(f"Session {self.session_id} authenticated with token: {study_token}")
    
    def set_scenario(self, scenario_id, condition, scenario_data):
        self.current_scenario_id = scenario_id
        self.current_condition = condition
        self.current_scenario_data = scenario_data
        
        self.token_rate_tokens_per_second = None
        
        self.feedback_submitted = False
        
        self.chat_history = []
        
        if scenario_id and scenario_id not in self.scenario_history:
            self.scenario_history.append(scenario_id)
            
        log_print(f"Session {self.session_id} assigned scenario: {scenario_id}, condition: {condition}")
    
    def get_scenario_question(self):
        if not self.current_scenario_data:
            return None
            
        return self.current_scenario_data.get("question")


class ChatApp:
    
    def __init__(self):
        log_print("Initializing chat application")
        
        self.current_dir = os.path.dirname(os.path.abspath(__file__))
        self.custom_css = load_asset(os.path.join(self.current_dir, "gradio_card.css"))
        self.js_content = load_asset(os.path.join(self.current_dir, "script.js"))
        
        self.app = gr.Blocks(
            theme=settings.Visuals.GRADIO_THEME,
            css=self.custom_css,
            elem_id="structured-ui",
            title="Interacting with AI Systems Study"
        )
        
        self.components = {}
    
    def launch(self):
        try:
            log_print("Launching application")
            self.build_interface()
            self.interface.queue(max_size=settings.QUEUE_SIZE).launch(
                server_name=settings.HOST,
                server_port=settings.PORT,
                debug=settings.DEBUG,
                show_error=settings.SHOW_ERROR,
                quiet=settings.QUIET
            )
            log_print("Application launched successfully")
        except Exception as e:
            log_print(f"Error launching application: {str(e)}")
            gr.Error("Die Anwendung konnte nicht gestartet werden. Bitte kontaktieren Sie den Administrator.")
            raise
    
    def build_interface(self):
        with gr.Blocks(analytics_enabled=False, css=self.custom_css, theme=settings.Visuals.GRADIO_THEME) as self.interface:
            self.components["session"] = gr.State(UserSession())
            
            self.components["message_state"] = gr.State("")
            self.components["feedback_success_state"] = gr.State(False)
            self.components["study_completed_state"] = gr.State(False)
            self.components["scenario_id_state"] = gr.State("")
            self.components["condition_state"] = gr.State("")
            
            with gr.Column(elem_id="app-container"):
                self._build_token_auth()
                
                with gr.Column(visible=False) as self.components["main_interface"]:
                    self._build_header()
                    
                    self._build_chat()
                    
                    self._build_input()
                    
                    self._build_feedback()
            
            self._setup_events()
            
            if self.js_content:
                gr.HTML(f"<script>{self.js_content}</script>")
        
        log_print("Interface built successfully")
        return self.interface
                                   
    
    def _build_header(self):
        header_text = ""
        header_description = ""
        header_task = ""
        
        header_title, header_description, header_task = UIComponents.create_header_section(
            header_text, header_description, header_task
        )
        
        self.components["header_title"] = header_title
        self.components["header_description"] = header_description
        self.components["header_task"] = header_task
        
        log_print("Header section built with enhanced styling")
    
    def _build_chat(self):
        chatbot = UIComponents.create_chat_interface()
        self.components["chatbot"] = chatbot
        log_print("Chat section built")
    
    def _build_input(self):
        user_input, send_btn = UIComponents.create_input_section()
        self.components["user_input"] = user_input
        self.components["send_btn"] = send_btn
        
        gr.Markdown("---", elem_classes=["section-divider"])
        log_print("Input section built")
    
    def _build_feedback(self):
        feedback_row, sliders, feedback_btn, next_scenario_btn = UIComponents.create_feedback_section()
        
        self.components["feedback_row"] = feedback_row
        self.components["sliders"] = sliders
        self.components["feedback_btn"] = feedback_btn
        self.components["next_scenario_btn"] = next_scenario_btn
        
        log_print("Feedback section built")
    
    def _build_token_auth(self):
        auth_row, token_input, auth_button = UIComponents.create_token_auth_section()
        
        self.components["auth_row"] = auth_row
        self.components["token_input"] = token_input
        self.components["auth_button"] = auth_button
        log_print("Token authentication section built")
    

    def _setup_events(self):
        self._setup_token_auth_events()
        self._setup_input_validation()
        self._setup_chat_events()
        self._setup_feedback_events()
        log_print("All events set up")
    
    def _setup_token_auth_events(self):
        self.components["auth_button"].click(
            fn=auth_model.validate_token,
            inputs=[
                self.components["token_input"],
                self.components["session"]
            ],
            outputs=[
                self.components["auth_row"],
                self.components["main_interface"],
                self.components["session"]
            ],
            queue=True
        ).then(
            fn=self._load_initial_scenario,
            inputs=[self.components["session"]],
            outputs=[
                self.components["header_title"],
                self.components["header_description"],
                self.components["header_task"],
                self.components["chatbot"],
                self.components["session"]
            ],
            queue=True
        )
    
    def _load_initial_scenario(self, session):
        try:
            locked_scenario_id, locked_condition = scenario_manager.task_distributor.find_locked_scenario_for_user(session.study_token)
            
            if locked_scenario_id and locked_condition:
                log_print(f"User {session.study_token} is continuing with locked scenario: {locked_scenario_id}, condition: {locked_condition}")
                scenario_id, condition = locked_scenario_id, locked_condition
            else:
                log_print(f"No locked scenario found for user {session.study_token}, selecting a new scenario")
                log_print("PRE-SELECT: About to call select_next_scenario_for_user for initial scenario...")
                scenario_id, condition = scenario_manager.task_distributor.select_next_scenario_for_user(session.study_token)
                log_print(f"POST-SELECT: selected_next_scenario_for_user returned: {scenario_id}, {condition}")
                
                if scenario_id and condition:
                    lock_file_path = os.path.join(scenario_manager.task_distributor.lock_file_base, f"{scenario_id}_{condition}.lock")
                    if os.path.exists(lock_file_path):
                        log_print(f"Lock file verified: {lock_file_path} exists for initial scenario")
                    else:
                        log_print(f"WARNING: Lock file doesn't exist for initial scenario: {lock_file_path}")
            
            if not scenario_id or not condition:
                scenario_data = settings.Scenario.COMPLETION_SCENARIO
                session.set_scenario("completed", None, scenario_data)
                session.study_completed = True
                
                completion_condition = scenario_data.get("condition", {})
                latency_setting = completion_condition.get("latency")
                if latency_setting:
                    session.response_delay = settings.Study.get_response_delay(latency_setting)
                    log_print(f"Completion scenario response delay: {session.response_delay}")
                
                log_print(f"User {session.study_token} has no available scenarios (completed)")
            else:
                scenario_path = os.path.join(scenario_manager.scenarios_dir, scenario_id, condition, "scenario.json")
                
                try:
                    with open(scenario_path, "r", encoding="utf-8") as f:
                        import json
                        scenario_data = json.load(f)
                    
                    session.set_scenario(scenario_id, condition, scenario_data)
                    
                    condition_config = scenario_data.get("condition", {})
                    log_print(f"Condition config: {condition_config}")
                    latency_setting = condition_config.get("latency")
                    log_print(f"Latency setting: {latency_setting}")
                    
                    if latency_setting:
                        session.response_delay = settings.Study.get_response_delay(latency_setting)
                        log_print(f"Response delay: {session.response_delay}")
                    
                except Exception as e:
                    log_print(f"Error loading scenario data: {str(e)}")
                    scenario_data = settings.Scenario.NO_SCENARIO_RESPONSE
                    session.set_scenario(None, None, scenario_data)
            
            title = scenario_data.get("title", "")
            description = scenario_data.get("description", "")
            task = scenario_data.get("task", "")
            welcome_message = scenario_data.get("welcome_message", "Error: No welcome message found.")
            
            formatted_title = f"# {title}"
            formatted_description = f"### {description}"
            formatted_task = f"*{task}*"
            
            chat_history = [gr.ChatMessage(role="assistant", content=welcome_message)]
            session.chat_history = chat_history
            
            log_print(f"Loaded initial scenario for user {session.session_id}: {scenario_id}, condition: {condition}")
            
            return formatted_title, formatted_description, formatted_task, chat_history, session
            
        except Exception as e:
            log_print(f"Error in _load_initial_scenario: {str(e)}")
            error_title = "# Error"
            error_description = "### Error loading initial scenario"
            error_task = "*Please try refreshing the page*"
            error_chat = [gr.ChatMessage(role="assistant", content="Error loading scenario data. Please refresh and try again.")]
            
            return error_title, error_description, error_task, error_chat, session
    
    def _setup_input_validation(self):
        self.components["user_input"].input(
            fn=chat_model.validate_input,
            inputs=[
                self.components["user_input"],
                self.components["session"]
            ],
            outputs=[self.components["send_btn"]],
            queue=True
        )
    
    def _check_session_timeout(self, user_input, chat_history, session):
        if session and session.is_timed_out():
            message = "Ihre Sitzung ist abgelaufen. Bitte laden Sie die Seite neu, um fortzufahren."
            
            system_message = {"role": "assistant", "content": message}
            updated_history = chat_history + [system_message]
            
            gr.Warning(message)
            
            return "", updated_history, ""
        
        return user_input, chat_history, user_input

    def _setup_chat_events(self):
        self._create_message_chain(self.components["send_btn"].click)
    
    def _create_message_chain(self, trigger_event):
        return trigger_event(
            fn=lambda: gr.update(interactive=False, variant="primary"),
            outputs=self.components["send_btn"],
            queue=False
        ).then(
            fn=self._check_session_timeout,
            inputs=[
                self.components["user_input"], 
                self.components["chatbot"],
                self.components["session"]
            ],
            outputs=[
                self.components["user_input"], 
                self.components["chatbot"], 
                self.components["message_state"]
            ],
            queue=False
        ).then(
            fn=chat_model.add_user_message,
            inputs=[
                self.components["message_state"],
                self.components["chatbot"],
                self.components["session"]
            ],
            outputs=[
                self.components["user_input"],
                self.components["chatbot"],
                self.components["message_state"]
            ],
            queue=False
        ).then(
            fn=chat_model.generate_streaming_response,
            inputs=[
                self.components["message_state"],
                self.components["chatbot"],
                self.components["session"]
            ],
            outputs=[
                self.components["user_input"],
                self.components["chatbot"]
            ],
            queue=True,
            show_progress="hidden"
        ).then(
            fn=self._show_feedback_with_session,
            inputs=[
                self.components["chatbot"],
                self.components["session"]
            ],
            outputs=[
                self.components["chatbot"],
                self.components["send_btn"],
                self.components["feedback_row"]
            ],
            queue=False
        ).then(
            fn=lambda: [gr.update(interactive=False), gr.update(interactive=False)],
            outputs=[self.components["send_btn"], self.components["user_input"]],
            queue=False
        )
        
    def _show_feedback_with_session(self, chat_history, session):
        session.chat_history = chat_history
        session.update_activity()
        
        gr.Info("Bitte geben Sie Ihr Feedback zur Antwort des KI-Systems!")
        return chat_history, gr.update(interactive=True), gr.update(visible=True)
    
    def _setup_feedback_events(self):
        self.components["feedback_btn"].click(
            fn=lambda: gr.update(interactive=False),
            outputs=[self.components["feedback_btn"]],
            queue=False 
        ).then(
            fn=self._prepare_feedback_submission,
            inputs=[self.components["session"]],
            outputs=[
                self.components["scenario_id_state"],
                self.components["condition_state"],
            ],
            queue=False
        ).then(
            fn=feedback_model.save_feedback,
            inputs=[
                self.components["scenario_id_state"],
                self.components["condition_state"],
                self.components["session"],
                *self.components["sliders"]
            ],
            outputs=[self.components["feedback_success_state"]]
        ).then(
            fn=self._check_and_update_completion_status,
            inputs=[
                self.components["feedback_success_state"],
                self.components["session"]
            ],
            outputs=[
                self.components["feedback_btn"],
                *self.components["sliders"],
                self.components["next_scenario_btn"],
                self.components["study_completed_state"],
                self.components["session"]
            ],
            queue=False
        )
        
        self.components["next_scenario_btn"].click(
            fn=self.load_next_scenario,
            inputs=[
                self.components["study_completed_state"],
                self.components["session"]
            ],
            outputs=[
                self.components["header_title"],
                self.components["header_description"],
                self.components["header_task"],
                self.components["chatbot"], 
                self.components["feedback_row"],
                self.components["next_scenario_btn"],
                *self.components["sliders"],
                self.components["feedback_btn"],
                self.components["user_input"],
                self.components["send_btn"],
                self.components["study_completed_state"],
                self.components["session"]
            ],
            queue=False
        )
    
    #-------------------------------------------------------------------------
    # BUSINESS LOGIC METHODS
    #-------------------------------------------------------------------------
    
    def _check_and_update_completion_status(self, feedback_success, session):
        if not feedback_success:
            gr.Warning("Feedback konnte nicht gespeichert werden. Bitte versuchen Sie es erneut.")
            return [
                gr.update(interactive=False),
                *[gr.update(interactive=False) for _ in range(len(settings.Feedback.SLIDER_CATEGORIES))],
                gr.update(visible=False),
                gr.update(value=False),
                session
            ]
        
        from gradio_app.models.scenario import scenario_manager
        task_distributor = scenario_manager.task_distributor
        
        if task_distributor:
            all_completed = task_distributor.has_user_completed_all_scenarios(session.study_token)
            session.study_completed = all_completed
        else:
            all_completed = False
        
        if all_completed:
            gr.Info("Herzlichen Glückwunsch! Sie haben alle Szenarien abgeschlossen.")
            return [
                gr.update(interactive=False),
                *[gr.update(interactive=False) for _ in range(len(settings.Feedback.SLIDER_CATEGORIES))],
                gr.update(visible=True, value=settings.Feedback.FEEDBACK_FINAL_SCENARIO_BUTTON_TEXT),
                gr.update(value=True),
                session
            ]
        else:
            gr.Info("Feedback erfolgreich gespeichert. Sie können nun zum nächsten Szenario fortfahren.")
            return [
                gr.update(interactive=False),
                *[gr.update(interactive=False) for _ in range(len(settings.Feedback.SLIDER_CATEGORIES))],
                gr.update(visible=True),
                gr.update(value=False),
                session
            ]
    
    def load_next_scenario(self, study_completed, session):
        try:
            if study_completed:
                log_print(f"User {session.study_token} has completed all scenarios")
                completed_scenario_data = settings.Scenario.COMPLETION_SCENARIO
                scenario_title = completed_scenario_data.get("title", "")
                scenario_description = completed_scenario_data.get("description", "")
                scenario_task = completed_scenario_data.get("task", "")
                welcome_message = completed_scenario_data.get("welcome_message", "")
                
                session.set_scenario("completed", None, completed_scenario_data)
                session.study_completed = True
                
                from gradio_app.models.scenario import scenario_manager
                task_distributor = scenario_manager.task_distributor
                if task_distributor and session.study_token:
                    task_distributor.release_all_user_locks(session.study_token)
                    log_print(f"Released all locks for user {session.study_token} upon study completion")
                
                new_chat = [gr.ChatMessage(role="assistant", content=welcome_message)]
                session.chat_history = new_chat
                
                log_print("Study completed. Browser will be redirected by frontend JavaScript.")
                
                formatted_title = f"# {scenario_title}"
                formatted_description = f"""### {scenario_description}"""
                formatted_task = f"""*{scenario_task}*"""
                
                next_btn_update = gr.update(
                    value=settings.Feedback.FEEDBACK_FINAL_SCENARIO_BUTTON_TEXT, 
                    visible=True,
                    elem_classes=["study-completed-btn"]
                )
                
                user_input_update = gr.update(
                    interactive=False,
                    placeholder="Die Studie ist abgeschlossen. Bitte klicke auf 'Weiter zum Fragebogen'.",
                    value=""
                )
                
                return [
                    gr.update(value=formatted_title),
                    gr.update(value=formatted_description),
                    gr.update(value=formatted_task),
                    new_chat,
                    gr.update(visible=False),
                    next_btn_update,
                    *[gr.update(value=settings.Feedback.SLIDER_DEFAULT_VALUE, interactive=False) for _ in self.components["sliders"]],
                    gr.update(interactive=False),
                    user_input_update,
                    gr.update(interactive=False),
                    gr.update(value=True),
                    session
                ]
            
            from gradio_app.models.scenario import scenario_manager
            task_distributor = scenario_manager.task_distributor
            
            if not task_distributor:
                gr.Warning("Task distributor not initialized properly")
                return [gr.update() for _ in range(11)] + [session]
            
            scenario_id, condition = task_distributor.select_next_scenario_for_user(session.study_token)
            
            if not scenario_id or not condition:
                gr.Info("Keine weiteren Szenarien verfügbar. Die Studie ist abgeschlossen!")
                session.study_completed = True
                
                completed_scenario_data = settings.Scenario.COMPLETION_SCENARIO
                session.set_scenario("completed", None, completed_scenario_data)
                
                new_chat = [gr.ChatMessage(role="assistant", content="Alle Szenarien abgeschlossen. Vielen Dank für Ihre Teilnahme!")]
                session.chat_history = new_chat
                
                return [
                    gr.update(value="# Studie abgeschlossen"),
                    gr.update(value="### Vielen Dank für Ihre Teilnahme!"),
                    gr.update(value="*Sie werden gleich zum Abschlussfragebogen weitergeleitet...*"),
                    new_chat,
                    gr.update(visible=False),
                    gr.update(visible=True, value="Weiter zum Fragebogen", elem_classes=["study-completed-btn"]),
                    *[gr.update(value=settings.Feedback.SLIDER_DEFAULT_VALUE, interactive=False) for _ in self.components["sliders"]],
                    gr.update(interactive=False),
                    gr.update(interactive=False, placeholder="Die Studie ist abgeschlossen."),
                    gr.update(interactive=False),
                    gr.update(value=True),
                    session
                ]
            
            scenario_path = os.path.join(scenario_manager.scenarios_dir, scenario_id, condition, "scenario.json")
            
            try:
                with open(scenario_path, "r", encoding="utf-8") as f:
                    import json
                    scenario_data = json.load(f)
                
                session.set_scenario(scenario_id, condition, scenario_data)
                
                condition_config = scenario_data.get("condition", {})
                log_print(f"Condition config: {condition_config}")
                latency_setting = condition_config.get("latency")
                log_print(f"Latency setting: {latency_setting}")
                
                if latency_setting:
                    session.response_delay = settings.Study.get_response_delay(latency_setting)
                    log_print(f"Response delay: {session.response_delay}")
                
            except Exception as e:
                log_print(f"Error loading scenario data: {str(e)}")
                gr.Warning(f"Fehler beim Laden des nächsten Szenarios: {str(e)}")
                
                scenario_data = {
                    "title": "Fehler",
                    "description": f"Fehler beim Laden des Szenarios {scenario_id}",
                    "task": "Bitte versuchen Sie es erneut oder kontaktieren Sie den Administrator.",
                    "welcome_message": f"Beim Laden des nächsten Szenarios ist ein Fehler aufgetreten: {str(e)}",
                    "condition": {"latency": "fast"}
                }
                
                session.set_scenario(None, None, scenario_data)
            
            scenario_title = scenario_data.get("title", "")
            scenario_description = scenario_data.get("description", "")
            scenario_task = scenario_data.get("task", "")
            welcome_message = scenario_data.get("welcome_message", "")
            
            if not welcome_message:
                log_print(f"Error: No welcome_message found in scenario data")
                gr.Warning("Fehlender Willkommenstext im Szenario. Bitte kontaktieren Sie den Administrator.")
                welcome_message = "Error: No welcome message found in scenario data."
                
            new_chat = [gr.ChatMessage(role="assistant", content=welcome_message)]
            session.chat_history = new_chat
            
            gr.Info("Neues Szenario wurde geladen.")
            log_print(f"Next scenario {scenario_id}, condition {condition} loaded for session {session.session_id}")
            
            formatted_title = f"# {scenario_title}"
            formatted_description = f"""### {scenario_description}"""
            formatted_task = f"""*{scenario_task}*"""
            
            session.feedback_submitted = False
            
            return [
                gr.update(value=formatted_title),
                gr.update(value=formatted_description),
                gr.update(value=formatted_task),
                new_chat,
                gr.update(visible=False),
                gr.update(visible=False, elem_classes=[]),
                *[gr.update(value=settings.Feedback.SLIDER_DEFAULT_VALUE, interactive=True) for _ in self.components["sliders"]],
                gr.update(interactive=True),
                gr.update(interactive=True, placeholder=settings.Chat.INPUT_TEXTBOX_HINT, value=""),
                gr.update(interactive=False),
                gr.update(value=False),
                session
            ]
            
        except Exception as e:
            log_print(f"Error loading next scenario: {str(e)}")
            gr.Error(f"Fehler beim Laden des nächsten Szenarios: {str(e)}")
            error_chat = [gr.ChatMessage(role="assistant", content="Error loading next scenario")]
            return [
                gr.update(value="# Error"),
                gr.update(value="\n### Error - no scenario data found."),
                gr.update(value="\n---\n*Error - no scenario data found.*"),
                error_chat,
                gr.update(visible=False),
                gr.update(visible=False),
                *[gr.update() for _ in self.components["sliders"]],
                gr.update(interactive=False),
                gr.update(interactive=False),
                gr.update(interactive=False),
                gr.update(value=False),
                session
            ]

    def _prepare_feedback_submission(self, session):
        if session.study_completed or session.current_scenario_id == "completed":
            log_print(f"Study is already completed for session {session.session_id}. Skipping feedback preparation.")
            return "completed", "none"
            
        current_scenario_id = session.current_scenario_id or "unknown"
        current_condition = session.current_condition or "unknown"
        
        log_print(f"Preparing feedback submission for session {session.session_id}: scenario: {current_scenario_id}, condition: {current_condition}")
        
        return current_scenario_id, current_condition


# Main entry point
if __name__ == "__main__":
    try:
        log_print("Starting Gradio app...")
        app = ChatApp()
        app.launch()
    except Exception as e:
        log_print(f"Fatal error starting application: {str(e)}")
        log_print(traceback.format_exc())
        sys.exit(1)