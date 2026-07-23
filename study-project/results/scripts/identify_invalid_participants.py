import pandas as pd
import os
import sys

# --- Configuration ---
DATA_ROOT_DIR = '../data'
ESSENTIAL_FILES = [
    'metadata.csv', 'pre_study.csv', 'main_study_conditions.csv', 'post_study.csv'
]
CORE_RATING_COLS = [
    'trustworthiness', 'accuracy', 'completeness', 'usefulness', 'comprehensibility'
]
EXPECTED_CONDITIONS = 4

# --- Helper Functions ---
def print_header(title):
    print("\n" + "="*60 + f"\n--- {title} ---\n" + "="*60 + "\n")

# --- Main Script Logic ---
def main():
    print_header("Participant Data Validity Check")

    data_root_path = os.path.abspath(DATA_ROOT_DIR)
    if not os.path.isdir(data_root_path):
        print(f"Error: Data directory not found at '{data_root_path}'", file=sys.stderr)
        sys.exit(1)

    participant_dir_names = [
        item for item in os.listdir(data_root_path)
        if os.path.isdir(os.path.join(data_root_path, item))
    ]

    if not participant_dir_names:
        print(f"No participant directories found in '{data_root_path}'.", file=sys.stderr)
        sys.exit(0)

    print(f"Found {len(participant_dir_names)} participant directories. Checking validity...")

    invalid_participants = {}

    for participant_id in participant_dir_names:
        p_dir_path = os.path.join(data_root_path, participant_id)
        reasons = []

        missing_files = [f for f in ESSENTIAL_FILES if not os.path.isfile(os.path.join(p_dir_path, f))]
        if missing_files:
            reasons.append(f"Missing essential files: {', '.join(missing_files)}")
            invalid_participants[participant_id] = reasons
            continue

        try:
            meta_file_path = os.path.join(p_dir_path, 'metadata.csv')
            df_meta = pd.read_csv(meta_file_path)
            if df_meta.empty or 'completionTimestamp' not in df_meta.columns or pd.isna(df_meta['completionTimestamp'].iloc[0]):
                 reasons.append("Study not marked as completed")

            post_file_path = os.path.join(p_dir_path, 'post_study.csv')
            df_post = pd.read_csv(post_file_path)
            if df_post.empty or 'completed' not in df_post.columns or not df_post['completed'].iloc[0]:
                reasons.append("Post-study questionnaire not marked as completed")

            main_file_path = os.path.join(p_dir_path, 'main_study_conditions.csv')
            df_main = pd.read_csv(main_file_path)
            if len(df_main) != EXPECTED_CONDITIONS:
                reasons.append(f"Expected {EXPECTED_CONDITIONS} condition rows, found {len(df_main)}")
            else:
                if df_main[CORE_RATING_COLS].isnull().any().any():
                    missing_cols = df_main[CORE_RATING_COLS].isnull().sum()
                    cols_with_missing = missing_cols[missing_cols > 0].index.tolist()
                    reasons.append(f"Missing ratings in core columns: {' '.join(cols_with_missing)}")

        except pd.errors.EmptyDataError as e:
            empty_filename = e.path if hasattr(e, 'path') else 'Unknown CSV'
            reasons.append(f"Empty CSV file: {os.path.basename(empty_filename)}")
        except FileNotFoundError as e:
            reasons.append(f"File not found during read: {os.path.basename(e.filename)}")
        except Exception as e:
            reasons.append(f"Error processing files: {type(e).__name__} - {e}")

        if reasons:
            invalid_participants[participant_id] = reasons

    print_header("Validity Check Results")
    if not invalid_participants:
        print("All participants appear valid.")
    else:
        print(f"Found {len(invalid_participants)} potentially invalid participants:")
        for participant_id, reason_list in invalid_participants.items():
            print(f"  - {participant_id}: {'; '.join(reason_list)}")

    print("\nCheck complete.")

if __name__ == "__main__":
    main() 