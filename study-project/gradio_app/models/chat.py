import time
import re
import random
import os
import json
import requests

import gradio as gr
from gradio_app.config import settings
from gradio_app.utils.logger import log_print
from gradio_app.models.scenario import scenario_manager
import spacy
import tiktoken

class ChatModel:
    def __init__(self):
        # Initializes the vectorizer with a larger model that includes word vectors
        try:
            self.vectorizer = spacy.load("de_core_news_md")  # Try to load medium-sized model first
        except OSError:
            import subprocess
            subprocess.run(["python", "-m", "spacy", "download", "de_core_news_md"])
            self.vectorizer = spacy.load("de_core_news_md")
        log_print("ChatModel initialized")
        
    # Adds a word delay to the response
    # e.g. random delay for every word between min and max delay and divide by base delay divisor
    def _get_word_delay(self):
        min_delay, max_delay = settings.Chat.RESPONSE_DELAY_RANGE
        base_delay = random.uniform(min_delay, max_delay) / settings.Chat.RESPONSE_BASE_DELAY_DIVISOR
        
        # Sometimes add a typing variance to the response delay based on a chance
        if random.random() < settings.Chat.TYPING_VARIANCE_CHANCE:
            base_delay *= settings.Chat.TYPING_VARIANCE_RESPONSE_DELAY_MULTIPLIER
            
        return base_delay
    
    # Adds an extra delay after punctuation
    def _apply_punctuation_delay(self, word, delay):
        if word and word[-1] in {'.', ',', '!', '?', ';'}:
            return delay * settings.Chat.PUNCTUATION_DELAY_MULTIPLIER
        return delay
    
    # Adds an extra delay after hesitation
    def _apply_hesitation_delay(self, delay):
        if random.random() < settings.Chat.EXTRA_HESITATION_PROBABILITY:
            return delay + settings.Chat.EXTRA_HESITATION_DELAY
        return delay
    
    # Generates a streaming response
    # Streams the response line by line with delays between words and lines
    def generate_streaming_response(self, user_message, chat_history, session):
        log_print(f"Generating streaming response for message: {user_message[:50]}...")
        
        # Sets up the assistant message in chat history
        assistant_message = {"role": "assistant", "content": ""}

        # Copies the chat history and appends the assistant message
        history = chat_history.copy()
        history.append(assistant_message)
        last_idx = len(history) - 1
        
        try:
            # Get the scenario specific to this user session
            scenario_id = session.current_scenario_id
            condition = session.current_condition
            
            # Session-specific response loading
            if not scenario_id or not condition:
                full_response = settings.Chat.NO_RESPONSE_MESSAGE
                log_print(f"No scenario/condition in session {session.session_id} for response loading")
            else:
                response_path = os.path.join(
                    scenario_manager.scenarios_dir, 
                    scenario_id, 
                    condition, 
                    "response.txt"
                )
                
                if not os.path.exists(response_path):
                    gr.Warning(f"Response file not found for scenario {scenario_id}/{condition}")
                    full_response = settings.Scenario.NO_RESPONSE_FILE
                else:
                    try:
                        with open(response_path, "r", encoding="utf-8") as f:
                            full_response = f.read()
                    except Exception as e:
                        log_print(f"Error loading response: {str(e)}")
                        gr.Warning(f"Error loading response: {str(e)}")
                        full_response = settings.Scenario.RESPONSE_ERROR
            
            # If no response, shows an error message in the chat
            if not full_response:
                log_print("No response to stream")
                gr.Warning("Keine Antwort für dieses Szenario gefunden.")
                history[last_idx] = {"role": "assistant", "content": settings.Chat.NO_RESPONSE_MESSAGE}
                yield "", history
                return
            
            tokenized_response = tiktoken.encoding_for_model(settings.Chat.TOKENIZER_MODEL_NAME).encode(full_response)
            log_print(f"Starting to stream response of length {len(tokenized_response)} tokens")
            
            # Adds initial thinking delay based on the scenario settings
            # from the session (e.g. slow vs fast condition)
            thinking_delay = session.response_delay
            time.sleep(thinking_delay)
            
            # Tracks the state for markdown formatting adjustments
            accumulated_text = ""
            in_code_block = False
            accumulated_tokens = []
            
            # Get the tokenizer for decoding
            tokenizer = tiktoken.encoding_for_model(settings.Chat.TOKENIZER_MODEL_NAME)
            
            # Variables to track tokens per second
            start_time = time.time()
            token_count = 0
            tokens_times = []
            
            # Process tokens one by one
            for i, token in enumerate(tokenized_response):
                token_count += 1
                accumulated_tokens.append(token)
                current_time = time.time()
                tokens_times.append(current_time)
                
                # Try to decode accumulated tokens
                try:
                    new_text = tokenizer.decode(accumulated_tokens)
                    token_text = new_text[len(accumulated_text):]  # Get just the new text
                    
                    # Check if this token contributes to a code block marker
                    if '```' in token_text:
                        in_code_block = not in_code_block
                        time.sleep(settings.Chat.CODE_BLOCK_MARKER_DELAY)
                    
                    # Calculate base delay for this token
                    delay = self._get_word_delay()
                    
                    # Apply punctuation delay if token contains punctuation
                    delay = self._apply_punctuation_delay(token_text, delay)
                    
                    # Apply hesitation delay
                    delay = self._apply_hesitation_delay(delay)
                    
                    # Apply the delay
                    time.sleep(delay)
                    
                    # Add token text to accumulated text
                    accumulated_text = new_text
                    
                    # Update history and yield response
                    history[last_idx] = {"role": "assistant", "content": accumulated_text}
                    yield "", history
                    
                    # Add extra delay for newlines
                    if '\n' in token_text:
                        time.sleep(settings.Chat.NEWLINE_DELAY)
                        
                except Exception as decode_error:
                    # If we can't decode yet, continue to next token
                    continue
            
            # Calculate tokens per second
            end_time = time.time()
            total_time = end_time - start_time
            
            if total_time > 0 and token_count > 0:
                tokens_per_second = token_count / total_time
                log_print(f"Tokens per second: {tokens_per_second:.2f} for scenario {scenario_id}/{condition}")
                
                # Save token rate directly to session for later use with feedback
                if scenario_id and condition:
                    # Store token rate in session
                    session.token_rate_tokens_per_second = tokens_per_second
                    log_print(f"Saved token rate ({tokens_per_second:.2f} tokens/sec) to session {session.session_id}")
            
            # Store the full chat history in the session
            session.chat_history = history
            session.update_activity()
                
            log_print("Finished streaming response")
            
        except Exception as e:
            log_print(f"Error in streaming response: {str(e)}")
            history[last_idx] = {"role": "assistant", "content": settings.Chat.ERROR_MESSAGE}
            yield "", history
            gr.Error(f"Problem bei der Generierung der Antwort: {str(e)}")
            raise gr.Error(settings.Chat.GENERATION_ERROR)
    
    # Adds a user message to the chat history
    def add_user_message(self, message, chat_history, session):
        log_print(f"Adding user message: {message[:50]}...")
        
        # Basic validation
        if not message or not message.strip():
            return "", chat_history, ""
        
        # Adds the user message to the chat history
        user_message = {"role": "user", "content": message.strip()}
        updated_history = chat_history + [user_message]
        
        # Update the session chat history and activity
        session.chat_history = updated_history
        session.update_activity()
        
        return "", updated_history, message.strip()
    
    # Validates the user input
    def validate_input(self, message, session):
        # Check if session is valid
        if not session:
            log_print("No valid session provided for input validation")
            return gr.update(interactive=False, variant="primary")
            
        # Update session activity
        session.update_activity()
        
        # Checks if the message is empty
        if not message or not message.strip():
            return gr.update(interactive=False, variant="primary")
        
        # Checks if the message is too short
        if len(message.strip()) < settings.Chat.MIN_MESSAGE_LENGTH:
            gr.Warning(f"Ihre Nachricht ist zu kurz. Bitte geben Sie mindestens {settings.Chat.MIN_MESSAGE_LENGTH} Zeichen ein.")
            return gr.update(interactive=False, variant="primary")
        
        # Checks if the message is too long
        if len(message.strip()) > settings.Chat.MAX_MESSAGE_LENGTH:
            gr.Warning(f"Ihre Nachricht ist zu lang. Bitte geben Sie maximal {settings.Chat.MAX_MESSAGE_LENGTH} Zeichen ein.")
            return gr.update(interactive=False, variant="primary")
        
        current_scenario_id = session.current_scenario_id
        
        # Disable input for completion scenario
        if current_scenario_id == "completed":
            log_print(f"Input disabled - study completed for session {session.session_id}")
            return gr.update(interactive=False, variant="secondary")
            
        current_question = session.get_scenario_question()
        log_print(f"Validating message against session {session.session_id} scenario {current_scenario_id} with question: {current_question}")
        
        # Validate only if we have a current scenario and question
        if current_scenario_id and current_question:
            if not self.validate_message_to_scenario_similarity(message, current_question):
                gr.Warning(f"{settings.Chat.MESSAGE_VALIDATION_NOT_SIMILAR} Erwartete Frage: {current_question}", visible=settings.Chat.MESSAGE_VALIDATION_NOT_SIMILAR_VISIBLE)
                return gr.update(interactive=False, variant="primary")
        else:
            log_print(f"Warning: No active scenario or question found for validation (ID: {current_scenario_id})")
            return gr.update(interactive=True, variant="primary")
        
        return gr.update(interactive=True, variant="primary")
    
    # Uses cosine similarity to calculate the similarity between the message and the scenario question
    def validate_message_to_scenario_similarity(self, message, scenario_question):
        # Converts the message and scenario question to vectors
        message_vector = self.vectorizer(message)
        scenario_question_vector = self.vectorizer(scenario_question)
        log_print(f"Message vector: {message_vector}")
        log_print(f"Scenario question vector: {scenario_question_vector}")

        # Calculates the cosine similarity
        similarity = message_vector.similarity(scenario_question_vector)
        log_print(f"Similarity: {similarity}")
        return similarity > settings.Chat.MESSAGE_TO_SCENARIO_SIMILARITY_THRESHOLD

# Create singleton instance
chat_model = ChatModel() 