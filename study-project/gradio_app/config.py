import os
import gradio as gr
from pydantic_settings import BaseSettings
import random

class GradioSettings:
    # Server settings
    PORT: int = 7861
    HOST: str = "0.0.0.0"
    DEBUG: bool = False  # If True, blocks the main thread from running.
    QUEUE_SIZE: int = 30
    SHOW_ERROR: bool = True
    QUIET: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = True

    class Visuals:
        # UI theme and appearance
        GRADIO_THEME = gr.themes.Soft()

    class Authentication:
        AUTH_INFO_MARKDOWN_HEADER = "## Authentifizierung"
        AUTH_INFO_MARKDOWN_DESCRIPTION = "Bitte gib deinen **Studien-Token** ein, um fortzufahren.\nDu solltest dieses Token vorhin erhalten haben."
        AUTH_TOKEN_INPUT_PLACEHOLDER = "Gib deinen Studien-Token hier ein..."
        AUTH_START_BUTTON_TEXT = "Studie starten"

    class Chat:
        # Message to scenario similarity threshold
        MESSAGE_TO_SCENARIO_SIMILARITY_THRESHOLD = 0.85 # Higher values means we enforce stricter similarity threshold
        MESSAGE_VALIDATION_NOT_SIMILAR = "Deine Frage entspricht noch nicht der Frage des aktuellen Szenarios. Bitte passe deine Nachricht an die aktuelle Frage an."
        MESSAGE_VALIDATION_NOT_SIMILAR_VISIBLE = False

        # Tokenizer model name
        TOKENIZER_MODEL_NAME = "gpt-4o"

        # Avatar settings
        AVATAR_FALLBACK_SVG_COLOR = "#4a90e2"
        AVATAR_SIZE = 48
        AVATAR_SCALE = 50
        AVATAR_RADIUS = 50

        # Avatar styles
        ASSISTANT_AVATAR_STYLE = "glass"
        USER_AVATAR_STYLE = "glass"
        ASSISTANT_AVATAR_SEED = "Aneka"
        USER_AVATAR_SEED = "Annalena"

        # Message validation
        MIN_MESSAGE_LENGTH = 3
        MAX_MESSAGE_LENGTH = 500
        MESSAGE_VALIDATION_TOO_LONG = "Ihre Frage ist zu lang. Bitte stellen Sie eine kürzere Frage."
        
        # UI text elements
        INPUT_TEXTBOX_HINT = "Stelle hier deine Frage..."
        INPUT_TEXTBOX_INFO = "__Beachte__: Deine Frage muss der oben genannten Fragestellung ähneln, damit du die Nachricht absenden kannst."
        # DEPRECATED: This default message should not be used, as all welcome messages should come from scenario.json files
        DEFAULT_INITIAL_MESSAGE = "Hey, hast du eine Frage, die du mir stellen möchtest?"
        SEND_BUTTON_TEXT = "Nachricht absenden"
        SEND_BUTTON_ICON_PATH = "images/icons/send_icon.svg"
        
        # Error messages with markdown
        NO_RESPONSE_MESSAGE = """## ⚠️ Keine Antwort verfügbar
        
Für dieses Szenario ist leider keine Antwort verfügbar."""
        
        ERROR_MESSAGE = """## ❌ Fehler
        
Ein Fehler ist aufgetreten. Bitte versuche es erneut."""

        GENERATION_ERROR = "Ein Fehler ist beim Generieren der Antwort aufgetreten."
        
        # Base delay settings
        FALLBACK_DELAY = 0.5  # Fallback "thinking" delay
        RESPONSE_DELAY_RANGE = [0.22125, 0.531]  # Typing speed range 
        RESPONSE_BASE_DELAY_DIVISOR = 16.95  # Divisor for base delay calculation 
        NEWLINE_DELAY = 0.0885  # Delay for empty line/newline 
        CODE_BLOCK_MARKER_DELAY = 0.22125  # Delay for code block markers 
        
        # Text streaming variations
        TYPING_VARIANCE_CHANCE = 0.177  # Chance for a typing variance 
        TYPING_VARIANCE_RESPONSE_DELAY_MULTIPLIER = 1.10625  # Multiplier for delay when thinking 
        PUNCTUATION_DELAY_MULTIPLIER = 0.7965  # Multiplier for delay when punctuation is detected 
        EXTRA_HESITATION_PROBABILITY = 0.1416   # 14.16% chance to add an extra pause mid-word 
        EXTRA_HESITATION_DELAY = 0.110625       # Additional delay in seconds for hesitation 
        
        # Markdown delay settings
        BLOCK_LEVEL_MARKDOWN_DELAY_MULTIPLIER = 0.885  # Multiplier for delay when markdown is detected 
        INLINE_MARKDOWN_DELAY_MULTIPLIER = 0.531  # Multiplier for delay when markdown is detected 
        
        # Code block specific delays
        CODE_BLOCK_START_DELAY_MULTIPLIER = 0.66375  # Multiplier for starting a code block 
        CODE_BLOCK_END_DELAY_MULTIPLIER = 0.885      # Multiplier for ending a code block 
        CODE_LINE_DELAY_MULTIPLIER = 0.44250          # Multiplier for each line in a code block 
        
        # Inline markdown closing delay multipliers
        MARKDOWN_DELAY_MULTIPLIERS = {
            "BOLD": 0.66375,           # Bold closing (e.g. ** or __) 
            "ITALIC": 0.531,           # Italic closing (e.g. * or _) 
            "INLINE_CODE": 0.7965,     # Inline code closing (e.g. `) 
            "STRIKETHROUGH": 0.57525,  # Strikethrough closing (e.g. ~~) 
            "LINK": 0.531,             # Link reference closing (e.g. ]) 
            "HEADER": 0.885,           # Header closing (e.g. #) 
            "LIST_ITEM": 0.61950,       # List item (e.g. -) 
            "BLOCK_QUOTE": 0.708,      # Block quote (e.g. >) 
            "TABLE": 0.61950,           # Table cell or row (e.g. |) 
            "HORIZONTAL_RULE": 0.75225, # Horizontal rule (e.g. ---) 
            "IMAGE": 0.66375,          # Image reference (e.g. ![alt text](image.png)) 
            "TASK_LIST": 0.57525,      # Task list item (e.g. - [ ] or - [x]) 
        }

    class Feedback:
        # Feedback categories
        SLIDER_CATEGORIES = [
            "Wahrgenommene Genauigkeit", 
            "Wahrgenommene Vollständigkeit", 
            "Wahrgenommene Nützlichkeit", 
            "Verständlichkeit", 
            "Vertrauen in die Antwort"
        ]
        
        # Slider info attributes with agreement scale descriptions
        SLIDER_INFO_ATTRIBUTES = {
            "Wahrgenommene Genauigkeit": "Stimmst du der folgenden Aussage zu? <b><i>\"Die Antwort war inhaltlich korrekt.\"</i></b><br>1 = stimme gar nicht zu, 7 = stimme voll zu",
            "Wahrgenommene Vollständigkeit": "Stimmst du der folgenden Aussage zu? <b><i>\"Die Antwort war vollständig - es fehlten keine wichtigen Informationen.\"</i></b><br>1 = stimme gar nicht zu, 7 = stimme voll zu",
            "Wahrgenommene Nützlichkeit": "Stimmst du der folgenden Aussage zu? <b><i>\"Die Antwort war für meine Informationssuche hilfreich.\"</i></b><br>1 = stimme gar nicht zu, 7 = stimme voll zu",
            "Verständlichkeit": "Stimmst du der folgenden Aussage zu? <b><i>\"Ich konnte die Antwort problemlos verstehen.\"</i></b><br>1 = stimme gar nicht zu, 7 = stimme voll zu",
            "Vertrauen in die Antwort": "Stimmst du der folgenden Aussage zu? <b><i>\"Ich vertraue den Informationen die mir in der Antwort gegeben wurden.\"</i></b><br>1 = stimme gar nicht zu, 7 = stimme voll zu"
        }
        
        # Slider configuration
        SLIDER_MIN = 1
        SLIDER_MAX = 7
        SLIDER_STEP = 1
        SLIDER_DEFAULT_VALUE = 4
        
        # UI text elements
        FEEDBACK_TITLE = "Feedback zur KI-Antwort"
        FEEDBACK_SUBMIT_BUTTON_TEXT = "Feedback absenden"
        FEEDBACK_SUBMIT_BUTTON_ICON_PATH = "images/icons/feedback_icon.svg"
        FEEDBACK_NEXT_SCENARIO_BUTTON_TEXT = "Nächstes Szenario"
        FEEDBACK_FINAL_SCENARIO_BUTTON_TEXT = "Weiter zum Fragebogen"
        
        # Error message text for modals
        FEEDBACK_COOKIE_FETCH_ERROR = "Beim Abrufen deines Nutzer-Tokens ist ein Fehler aufgetreten. Bitte lösche deine Cookies und Browser-Daten und beginne die Studie von vorne."
        
        # Delay and timeout settings
        FEEDBACK_CONFIRMATION_DELAY = 0.5  # Delay after saving feedback before showing confirmation
        FEEDBACK_COOKIE_FETCH_TIMEOUT = 10.0  # Timeout for fetching the study token cookie

    class Scenario:
        # Scenario messages with markdown
        NO_SCENARIO_RESPONSE = """## ⚠️ Keine Antwort verfügbar
        
Es ist keine Antwort für dieses Szenario verfügbar."""
        
        NO_RESPONSE_FILE = """## ⚠️ Datei nicht gefunden
        
Die Antwortdatei für dieses Szenario und diese Bedingung wurde nicht gefunden."""
        
        RESPONSE_ERROR = """## ❌ Fehler beim Laden
        
Beim Laden der Antwort ist ein Fehler aufgetreten."""

        # Completion scenario data - used when all scenarios are completed
        COMPLETION_SCENARIO = {
            "title": "Studie abgeschlossen",
            "description": "Vielen Dank! Du hast alle Szenarien abgeschlossen.",
            "question": "Studie abgeschlossen. Keine weitere Frage verfügbar.",
            "task": "Du wirst gleich automatisch zum Fragebogen weitergeleitet...",
            "header": "Hauptteil abgeschlossen",
            "welcome_message": "Vielen Dank für deine Teilnahme! Du hast nun alle Szenarien abgeschlossen. Du wirst gleich automatisch zum Fragebogen weitergeleitet.",
            "condition": {"latency": "fast", "complexity": "easy"}
        }

    class Study:
        # Latency ranges for different conditions
        LATENCY_RANGES = {
            "fast": (0.7, 0.9),  # Fast response time range: between 0.7 and 0.9 seconds thinking delay
            "slow": (5.0, 6.0)   # Slow response time range: between 5.0 and 6.0 seconds thinking delay
        }
        
        @staticmethod
        def get_response_delay(latency_type):
            if not latency_type:
                return GradioSettings.Chat.FALLBACK_DELAY
                
            latency_range = GradioSettings.Study.LATENCY_RANGES.get(latency_type)
            if not latency_range:
                return GradioSettings.Chat.FALLBACK_DELAY
                
            min_delay, max_delay = latency_range
            return random.uniform(min_delay, max_delay)

    class Logging:
        ENABLED = True
        FORMAT = "[{filename}] {message}"

settings = GradioSettings()