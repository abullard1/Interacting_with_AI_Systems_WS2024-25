# File: backend/app/core/firebase.py
import logging
from typing import Dict, Any
from firebase_admin import firestore, firestore_async
from datetime import datetime
import os
import json
import glob
import sys

logger = logging.getLogger(__name__)

async def store_study_data(data: Dict[Any, Any]) -> None:
  study_token = data.get("study_token")
  timestamp = data.get("timestamp")
  
  feedback_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 
                             "gradio_app", "feedback", study_token)
  
  if not os.path.exists(feedback_dir):
    logger.warning(f"Feedback directory does not exist for user {study_token}. Creating empty directory.")
    try:
      os.makedirs(feedback_dir, exist_ok=True)
    except Exception as e:
      logger.error(f"Error creating feedback directory for user {study_token}: {str(e)}")
      raise ValueError(f"Could not create feedback directory for user {study_token}")
  
  db = firestore_async.client()
  
  user_doc_ref = db.collection('users').document(study_token)
  
  try:
    user_doc = await user_doc_ref.get()
    if not user_doc.exists:
      logger.error(f"User document not found for {study_token}")
      raise ValueError(f"User document not found for {study_token}")
    
    user_data = user_doc.to_dict()
    
    if 'mainStudy' not in user_data:
      user_data['mainStudy'] = {'scenarios': {}}
    elif 'scenarios' not in user_data['mainStudy']:
      user_data['mainStudy']['scenarios'] = {}
      
    all_json_files = glob.glob(os.path.join(feedback_dir, "*.json"))
    feedback_files = [f for f in all_json_files if os.path.basename(f).startswith('feedback_')]
    
    logger.info(f"Found {len(all_json_files)} JSON files, {len(feedback_files)} are feedback files for user {study_token}")
    
    if len(feedback_files) == 0:
      logger.warning(f"No feedback files found for user {study_token}. Proceeding with empty feedback data.")
    else:
      for file_path in feedback_files:
        try:
          with open(file_path, 'r') as f:
            feedback = json.load(f)
            
            if 'condition' in feedback and 'scenario_id' in feedback and 'ratings' in feedback:
              # Map condition string (e.g., "fast-easy") to Firestore field name (e.g., "fast_easy")
              condition_parts = feedback['condition'].split('-')
              if len(condition_parts) == 2:
                speed, complexity = condition_parts
                field_key = f"{speed}_{complexity}"
                
                if field_key not in user_data['mainStudy']['scenarios']:
                  user_data['mainStudy']['scenarios'][field_key] = {
                    'scenario_id': feedback['scenario_id'],
                    'feedback': {}
                  }
                else:
                  user_data['mainStudy']['scenarios'][field_key]['scenario_id'] = feedback['scenario_id']
                  if 'feedback' not in user_data['mainStudy']['scenarios'][field_key]:
                    user_data['mainStudy']['scenarios'][field_key]['feedback'] = {}
                
                # Populate feedback ratings, mapping German keys to camelCase
                user_data['mainStudy']['scenarios'][field_key]['feedback'] = {
                  "wahrgenommeneGenauigkeit": feedback['ratings'].get('Wahrgenommene Genauigkeit'),
                  "wahrgenommeneVollständigkeit": feedback['ratings'].get('Wahrgenommene Vollständigkeit'),
                  "wahrgenommeneNützlichkeit": feedback['ratings'].get('Wahrgenommene Nützlichkeit'),
                  "verständlichkeit": feedback['ratings'].get('Verständlichkeit'),
                  "vertrauenInDieAntwort": feedback['ratings'].get('Vertrauen in die Antwort')
                }
                
                if 'timestamp' in feedback:
                  user_data['mainStudy']['scenarios'][field_key]['timestamp'] = feedback['timestamp']
                
                # Add token rate if available and valid
                if 'tokens_per_second' in feedback:
                  try:
                    # Ensure token rate is a valid float before storing
                    token_rate = float(feedback['tokens_per_second'])
                    user_data['mainStudy']['scenarios'][field_key]['tokens_per_second'] = token_rate
                    logger.info(f"Added token rate data ({token_rate:.2f} tokens/sec) to Firebase for user {study_token}, scenario {field_key}")
                  except (ValueError, TypeError) as e:
                    logger.warning(f"Skipped invalid token rate data for user {study_token}, scenario {field_key}: {str(e)}")
                
                # Add response delay if available and valid
                if 'response_delay_seconds' in feedback:
                  try:
                    # Ensure response delay is a valid float before storing
                    response_delay = float(feedback['response_delay_seconds'])
                    user_data['mainStudy']['scenarios'][field_key]['response_delay_seconds'] = response_delay
                    logger.info(f"Added response delay data ({response_delay:.2f} seconds) to Firebase for user {study_token}, scenario {field_key}")
                  except (ValueError, TypeError) as e:
                    logger.warning(f"Skipped invalid response delay data for user {study_token}, scenario {field_key}: {str(e)}")
                
                for key, value in feedback.items():
                  if key not in ('ratings', 'scenario_id', 'condition', 'timestamp', 'tokens_per_second', 'response_delay_seconds'):
                    user_data['mainStudy']['scenarios'][field_key][key] = value
                    logger.info(f"Added additional field '{key}' to Firebase for user {study_token}, scenario {field_key}")
        except Exception as e:
          logger.error(f"Error processing feedback file {os.path.basename(file_path)}: {str(e)}")
    
    feedback_count = len(user_data['mainStudy']['scenarios'])
    
    await user_doc_ref.update({
      'mainStudy': user_data['mainStudy'],
      'gradio_study_completion_timestamp': timestamp
    })
    
    logger.info(f"Updated mainStudy.scenarios structure for user {study_token} with {feedback_count} scenario entries")
    
    await release_user_locks(study_token)
    
    logger.info(f"Successfully stored study data for user {study_token} with {feedback_count} scenario entries.")
    
  except Exception as e:
    logger.error(f"Error storing study data for user {study_token}: {str(e)}")
    raise e
  
async def release_user_locks(study_token: str) -> None:
  logger.info(f"[LOCK_RELEASE] Attempting to release locks for user {study_token}")
  try:
    gradio_app_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 
                                  "gradio_app")
    locks_dir = os.path.join(gradio_app_path, "feedback", "locks")
    
    if not os.path.exists(locks_dir):
      logger.warning(f"[LOCK_RELEASE] Locks directory does not exist: {locks_dir}")
      try:
        os.makedirs(locks_dir, exist_ok=True)
        logger.info(f"[LOCK_RELEASE] Created locks directory: {locks_dir}")
      except Exception as e:
        logger.error(f"[LOCK_RELEASE] Error creating locks directory: {str(e)}")
      return
    
    try:
      lock_files = [os.path.join(locks_dir, f) for f in os.listdir(locks_dir) if f.endswith('.lock')]
      logger.info(f"[LOCK_RELEASE] Found {len(lock_files)} lock files before release")
    except Exception as e:
      logger.error(f"[LOCK_RELEASE] Error listing lock files: {str(e)}")
      return
    
    removed_count = 0
    for lock_file_path in lock_files:
      try:
        with open(lock_file_path, 'r') as f:
          lock_content = f.read().strip()
          
        if study_token in lock_content:
          logger.info(f"[LOCK_RELEASE] Removing lock file for user {study_token}: {os.path.basename(lock_file_path)}")
          try:
            os.remove(lock_file_path)
            removed_count += 1
          except PermissionError:
            logger.warning(f"[LOCK_RELEASE] Permission denied when removing lock file: {os.path.basename(lock_file_path)}")
          except FileNotFoundError:
            logger.warning(f"[LOCK_RELEASE] Lock file no longer exists: {os.path.basename(lock_file_path)}")
          except Exception as remove_error:
            logger.error(f"[LOCK_RELEASE] Error removing lock file {os.path.basename(lock_file_path)}: {str(remove_error)}")
        
      except Exception as e:
        logger.error(f"[LOCK_RELEASE] Error processing lock file {os.path.basename(lock_file_path)}: {str(e)}")
    
    try:
      remaining_files = len([f for f in os.listdir(locks_dir) if f.endswith('.lock')])
      logger.info(f"[LOCK_RELEASE] Removed {removed_count} lock files. {remaining_files} remaining.")
    except Exception as e:
      logger.error(f"[LOCK_RELEASE] Error counting remaining lock files: {str(e)}")
    
  except Exception as e:
    logger.error(f"[LOCK_RELEASE] Error in release_user_locks for user {study_token}: {str(e)}")
  
