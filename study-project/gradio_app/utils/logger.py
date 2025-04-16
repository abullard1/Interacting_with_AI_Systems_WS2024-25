import os
import inspect
from gradio_app.config import GradioSettings

def log_print(message):
    if GradioSettings.Logging.ENABLED:
        caller_frame = inspect.stack()[1]
        filename = os.path.basename(caller_frame.filename)

        formatted_message = GradioSettings.Logging.FORMAT.format(
            filename=filename,
            message=message
        )
        print(formatted_message)
