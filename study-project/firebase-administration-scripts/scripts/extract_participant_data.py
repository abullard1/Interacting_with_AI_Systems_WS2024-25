import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
import os
import json
import sys

# --- Configuration ---
SERVICE_ACCOUNT_KEY_PATH = '../firebase_adminsdk_key.json'
FIRESTORE_PROJECT_ID = 'interacting-with-ai-systems'
FEEDBACK_DIR_RELATIVE = '../../gradio_app/feedback'
OUTPUT_ROOT_DIR_RELATIVE = '../../results/data'

# Mapping from German JSON keys to English DataFrame columns
RATING_KEY_MAP = {
    "Wahrgenommene Genauigkeit": "accuracy",
    "Wahrgenommene Vollständigkeit": "completeness",
    "Wahrgenommene Nützlichkeit": "usefulness",
    "Verständlichkeit": "comprehensibility",
    "Vertrauen in die Antwort": "trustworthiness"
}

# Define expected condition keys
CONDITION_KEYS = ['slow_easy', 'fast_easy', 'slow_hard', 'fast_hard']

IGNORE_DIRS = ['locks', 'abandoned']

# --- Firebase Initialization ---
def initialize_firebase():
    """Initializes the Firebase Admin SDK if not already initialized."""
    if not firebase_admin._apps:
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            key_path_absolute = os.path.join(script_dir, SERVICE_ACCOUNT_KEY_PATH)

            if not os.path.exists(key_path_absolute):
                print(f"Error: Service account key not found at {key_path_absolute}", file=sys.stderr)
                sys.exit(1)

            cred = credentials.Certificate(key_path_absolute)
            firebase_admin.initialize_app(cred, {'projectId': FIRESTORE_PROJECT_ID})
            db = firestore.client()
            print("Firebase Admin SDK initialized successfully.")
            return db
        except Exception as e:
            print(f"Error initializing Firebase Admin SDK: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print("Firebase Admin SDK already initialized.")
        return firestore.client()

# --- Load Feedback Data from JSON --- #
def load_feedback_from_json(script_dir):
    """Loads feedback ratings from JSON files, ignoring specified directories."""
    print(f"Scanning feedback directory: {FEEDBACK_DIR_RELATIVE}")
    feedback_data = {} # {participant_id: {condition_key: {ratings...}}}
    feedback_dir_absolute = os.path.abspath(os.path.join(script_dir, FEEDBACK_DIR_RELATIVE))

    if not os.path.isdir(feedback_dir_absolute):
        print(f"Error: Feedback directory not found at {feedback_dir_absolute}", file=sys.stderr)
        return None

    valid_participant_dirs = []
    for item_name in os.listdir(feedback_dir_absolute):
        item_path = os.path.join(feedback_dir_absolute, item_name)
        if os.path.isdir(item_path) and item_name not in IGNORE_DIRS:
            valid_participant_dirs.append(item_name)

    print(f"Found {len(valid_participant_dirs)} potential participant directories (excluding ignored).")

    for participant_id in valid_participant_dirs:
        participant_path = os.path.join(feedback_dir_absolute, participant_id)
        feedback_data[participant_id] = {}

        json_files = []
        for filename in os.listdir(participant_path):
            if filename.endswith('.json') and filename.startswith('feedback_'):
                json_files.append(os.path.join(participant_path, filename))

        for file_path in json_files:
            filename = os.path.basename(file_path)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                condition = data.get('condition')
                ratings = data.get('ratings')

                if condition and ratings:
                    normalized_condition = condition.replace('-', '_').lower()
                    if normalized_condition in CONDITION_KEYS:
                        mapped_ratings = {}
                        for key_german, value in ratings.items():
                            key_english = RATING_KEY_MAP.get(key_german)
                            if key_english:
                                mapped_ratings[key_english] = value

                        if normalized_condition not in feedback_data[participant_id]:
                            feedback_data[participant_id][normalized_condition] = mapped_ratings
                        else:
                            print(f"    Warning: Duplicate JSON data found for participant {participant_id}, condition {normalized_condition}. Keeping first found.", file=sys.stderr)
                    else:
                        print(f"    Warning: Skipping file {filename} due to unrecognized condition '{condition}'.", file=sys.stderr)
                else:
                    print(f"    Warning: Skipping file {filename} due to missing 'condition' or 'ratings'.", file=sys.stderr)
            except json.JSONDecodeError:
                print(f"    Warning: Skipping file {filename} due to invalid JSON.", file=sys.stderr)
            except Exception as e:
                print(f"    Warning: Error processing file {filename}: {e}", file=sys.stderr)

    final_feedback_data = {}
    for pid, data in feedback_data.items():
        if data:
            final_feedback_data[pid] = data

    print(f"Finished processing JSON files. Found feedback data for {len(final_feedback_data)} participants.")
    return final_feedback_data

# --- Fetch Firestore Data --- #
def fetch_firestore_data(db, participant_ids):
    """Fetches full Firestore documents for the given participant IDs."""
    print(f"Fetching Firestore data for {len(participant_ids)} participants...")
    users_ref = db.collection('users')
    MAX_IN_QUERY_SIZE = 30
    firestore_user_data = {}

    for i in range(0, len(participant_ids), MAX_IN_QUERY_SIZE):
        batch_ids = participant_ids[i:i + MAX_IN_QUERY_SIZE]
        try:
            docs = users_ref.where('__name__', 'in', batch_ids).stream()
            for doc in docs:
                firestore_user_data[doc.id] = doc.to_dict()
        except Exception as e:
            print(f"Warning: Error fetching Firestore batch ({i // MAX_IN_QUERY_SIZE + 1}): {e}", file=sys.stderr)

    print(f"Fetched Firestore data for {len(firestore_user_data)} participants.")
    missing_in_firestore = len(participant_ids) - len(firestore_user_data)
    if missing_in_firestore > 0:
         print(f"Warning: {missing_in_firestore} participants had feedback folders but no matching Firestore document.")
    return firestore_user_data

# --- Save Flattened Data --- #
def save_flattened_csv(data_dict, participant_id, participant_output_dir, section_name, filename, index=False):
    """Flattens a dictionary using json_normalize and saves it as a CSV."""
    if data_dict:
        try:
            df = pd.json_normalize(data_dict, sep='_')
            if not index:
                df.insert(0, 'participant_id', participant_id)
            output_path = os.path.join(participant_output_dir, filename)
            df.to_csv(output_path, index=index, encoding='utf-8')
        except Exception as e:
            print(f"    Error processing/saving {section_name} data for {participant_id}: {e}", file=sys.stderr)
    else:
        output_path = os.path.join(participant_output_dir, filename)
        with open(output_path, 'w') as f:
            pass
        print(f"    Note: No {section_name} data found for {participant_id}. Created empty {filename}.")

# --- Process and Save Participant Data --- #
def process_participant(participant_id, firestore_data, feedback_ratings, output_dir):
    """Processes a single participant's data and saves the CSV files."""
    participant_output_dir = os.path.join(output_dir, participant_id)
    os.makedirs(participant_output_dir, exist_ok=True)

    exclude_keys = ['preStudyQuestionnaire', 'mainStudy', 'postStudyQuestionnaire', 'studyCompensation']
    metadata = {}
    for key, value in firestore_data.items():
        if key not in exclude_keys:
            metadata[key] = value
    device_info = firestore_data.get('deviceInfo', {})
    metadata.update(device_info)
    save_flattened_csv(metadata, participant_id, participant_output_dir, 'metadata', 'metadata.csv')

    pre_study_data = firestore_data.get('preStudyQuestionnaire')
    save_flattened_csv(pre_study_data, participant_id, participant_output_dir, 'pre-study', 'pre_study.csv')

    main_study_section = firestore_data.get('mainStudy', {})
    main_study_top_level = {}
    for key, value in main_study_section.items():
        if key != 'scenarios':
            main_study_top_level[key] = value

    scenarios_data = main_study_section.get('scenarios', {})
    condition_rows = []

    for condition_key in CONDITION_KEYS:
        condition_firestore_data = scenarios_data.get(condition_key, {})
        condition_feedback_json = feedback_ratings.get(condition_key, {})

        filtered_fs_data = {}
        for key, value in condition_firestore_data.items():
            if key != 'feedback':
                filtered_fs_data[key] = value

        row_data = {
            'participant_id': participant_id,
            'condition': condition_key
        }
        row_data.update(main_study_top_level)
        row_data.update(filtered_fs_data)
        row_data.update(condition_feedback_json)

        condition_rows.append(row_data)

    if condition_rows:
        try:
            main_study_df = pd.json_normalize(condition_rows, sep='_')
            cols_start = ['participant_id', 'condition']
            cols_end = []
            for col in main_study_df.columns:
                if col not in cols_start:
                    cols_end.append(col)
            final_cols = cols_start + cols_end
            main_study_df = main_study_df[final_cols]
            save_flattened_csv(main_study_df, participant_id, participant_output_dir, 'main study conditions', 'main_study_conditions.csv', index=True)

        except Exception as e:
            print(f"    Error processing/saving main study data for {participant_id}: {e}", file=sys.stderr)
    else:
        output_path = os.path.join(participant_output_dir, 'main_study_conditions.csv')
        with open(output_path, 'w') as f:
            pass
        print(f"    Note: No main study condition data processed for {participant_id}. Created empty main_study_conditions.csv.")

    post_study_data = firestore_data.get('postStudyQuestionnaire')
    save_flattened_csv(post_study_data, participant_id, participant_output_dir, 'post-study', 'post_study.csv')

    compensation_data = firestore_data.get('studyCompensation')
    save_flattened_csv(compensation_data, participant_id, participant_output_dir, 'compensation', 'compensation.csv')

# --- Main Execution --- #
def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db = initialize_firebase()

    feedback_data = load_feedback_from_json(script_dir)
    if feedback_data is None:
        sys.exit(1)

    participant_ids_with_feedback = list(feedback_data.keys())
    if not participant_ids_with_feedback:
        print("No participants found with valid feedback data. Exiting.")
        sys.exit(0)

    firestore_data = fetch_firestore_data(db, participant_ids_with_feedback)

    output_root_absolute = os.path.abspath(os.path.join(script_dir, OUTPUT_ROOT_DIR_RELATIVE))
    os.makedirs(output_root_absolute, exist_ok=True)
    print(f"Output will be saved in: {output_root_absolute}")

    processed_count = 0
    skipped_count = 0

    for participant_id in participant_ids_with_feedback:
        if participant_id in firestore_data:
            print(f"Processing participant: {participant_id}")
            process_participant(
                participant_id,
                firestore_data[participant_id],
                feedback_data[participant_id],
                output_root_absolute
            )
            processed_count += 1
        else:
            print(f"Skipping participant {participant_id}: Found in feedback JSONs but missing in Firestore.", file=sys.stderr)
            skipped_count += 1

    print(f"\nFinished processing. Extracted data for {processed_count} participants.")
    if skipped_count > 0:
        print(f"Skipped {skipped_count} participants due to missing Firestore data.")
    print("Script finished.")

if __name__ == "__main__":
    main() 