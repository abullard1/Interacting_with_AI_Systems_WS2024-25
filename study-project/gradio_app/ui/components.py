import gradio as gr
from dicebear import create_avatar

from gradio_app.config import settings
from gradio_app.utils.logger import log_print

class UIComponents:
    @staticmethod
    def create_chat_interface():
        with gr.Row(elem_classes=["card", "chat-section"]):
            with gr.Column(scale=12):
                avatar_pair = UIComponents._create_avatar_pair()

                initial_messages = []
                
                chatbot = gr.Chatbot(
                    value=initial_messages,
                    type="messages", 
                    height=600,
                    avatar_images=avatar_pair,
                    elem_id="chat-container",
                    autoscroll=True
                )
                
                log_print("Chat interface created")
                return chatbot
    
    @staticmethod
    def _create_avatar_pair():
        avatar_settings = {
            'scale': settings.Chat.AVATAR_SCALE,
            'radius': settings.Chat.AVATAR_RADIUS,
            'size': settings.Chat.AVATAR_SIZE,
            'backgroundType': "solid"
        }
        
        try:
            user_avatar = create_avatar(
                style=settings.Chat.USER_AVATAR_STYLE,
                seed=settings.Chat.USER_AVATAR_SEED,
                customisations=avatar_settings
            )
            assistant_avatar = create_avatar(
                style=settings.Chat.ASSISTANT_AVATAR_STYLE,
                seed=settings.Chat.ASSISTANT_AVATAR_SEED,
                customisations=avatar_settings
            )
            
            log_print("Avatar pair created successfully")
            return (user_avatar.url_svg, assistant_avatar.url_svg)
        except Exception as e:
            log_print(f"Error creating avatars: {str(e)}")
            default_svg = f'<svg width="{settings.Chat.AVATAR_SIZE}" height="{settings.Chat.AVATAR_SIZE}" xmlns="http://www.w3.org/2000/svg"><circle cx="24" cy="24" r="24" fill="{settings.Chat.AVATAR_FALLBACK_SVG_COLOR}"/></svg>'
            return (default_svg, default_svg)
    
    @staticmethod
    def create_input_section():
        with gr.Row(elem_classes=["card", "input-section-row"]):
            with gr.Column(scale=1, elem_classes=["input-container-column"]):
                user_input = gr.Textbox(
                    placeholder=settings.Chat.INPUT_TEXTBOX_HINT,
                    autofocus=False,
                    show_label=False,
                    elem_id="user-input-box",
                    elem_classes=["user-input"],
                    container=True,
                    lines=2,
                    info=settings.Chat.INPUT_TEXTBOX_INFO,
                    max_lines=8,
                    max_length=settings.Chat.MAX_MESSAGE_LENGTH
                )
                
                send_btn = gr.Button(
                    value=settings.Chat.SEND_BUTTON_TEXT,
                    variant="primary",
                    elem_id="send-btn",
                    elem_classes=["send-button"],
                    size="lg",
                    interactive=False,
                    icon=settings.Chat.SEND_BUTTON_ICON_PATH
                )
        
        log_print("Input section created")
        return user_input, send_btn
    
    @staticmethod
    def create_feedback_section():
        with gr.Row(elem_classes=["card"], visible=False) as feedback_row:
            with gr.Column(scale=10):
                gr.Markdown(settings.Feedback.FEEDBACK_TITLE, elem_id="feedback-title")
                
                sliders = UIComponents._create_feedback_sliders()

                feedback_btn = gr.Button(
                    value=settings.Feedback.FEEDBACK_SUBMIT_BUTTON_TEXT,
                    variant="primary",
                    elem_id="feedback-submit-btn",
                    icon=settings.Feedback.FEEDBACK_SUBMIT_BUTTON_ICON_PATH
                )
                
                next_scenario_btn = gr.Button(
                    value=settings.Feedback.FEEDBACK_NEXT_SCENARIO_BUTTON_TEXT,
                    variant="secondary",
                    elem_id="next-scenario-btn",
                    visible=False
                )
        
        log_print("Feedback section created")
        return feedback_row, sliders, feedback_btn, next_scenario_btn
    
    @staticmethod
    def _create_feedback_sliders():
        sliders = []
        for category in settings.Feedback.SLIDER_CATEGORIES:
            slider = gr.Slider(
                minimum=settings.Feedback.SLIDER_MIN,
                maximum=settings.Feedback.SLIDER_MAX,
                step=settings.Feedback.SLIDER_STEP,
                label=category,
                info=settings.Feedback.SLIDER_INFO_ATTRIBUTES[category],
                value=settings.Feedback.SLIDER_DEFAULT_VALUE,
                elem_id=f"{category.lower().replace(' ', '-')}-slider",
                elem_classes=["feedback-slider"]
            )
            sliders.append(slider)
        return sliders
    
    @staticmethod
    def create_header_section(initial_title="", initial_description="", initial_task=""):
        with gr.Row(elem_classes=["card", "scenario-header-card"]):
            with gr.Column():
                header_title = gr.Markdown(
                    value=f"""# {initial_title}""",
                    elem_classes=["header-title", "scenario-title"],
                    elem_id="scenario-title"
                )
                header_description = gr.Markdown(
                    value=f"""### {initial_description}""",
                    elem_classes=["header-description", "scenario-description"], 
                    elem_id="scenario-description"
                )
                header_task = gr.Markdown(
                    value=initial_task,
                    elem_classes=["header-task", "scenario-task"],
                    elem_id="scenario-task"
                )
        
        log_print("Header section created with enhanced styling")
        return header_title, header_description, header_task
    
    @staticmethod
    def create_token_auth_section():
        with gr.Row(elem_classes=["auth-section"]) as auth_row:
            with gr.Column():
                gr.Markdown(settings.Authentication.AUTH_INFO_MARKDOWN_HEADER, elem_classes=["auth-header"])
                gr.Markdown(
                    settings.Authentication.AUTH_INFO_MARKDOWN_DESCRIPTION,
                    elem_classes=["auth-description"]
                )
                
                token_input = gr.Textbox(
                    label="Study Token", 
                    placeholder=settings.Authentication.AUTH_TOKEN_INPUT_PLACEHOLDER,
                    elem_classes=["token-input"]
                )
                
                auth_button = gr.Button(
                    settings.Authentication.AUTH_START_BUTTON_TEXT, 
                    variant="primary",
                    elem_classes=["auth-button"]
                )
        
        log_print("Token authentication section built")
        return auth_row, token_input, auth_button