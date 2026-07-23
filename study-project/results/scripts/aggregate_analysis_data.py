import pandas as pd
import os
import sys

# --- Configuration ---
PARTICIPANT_DATA_DIR = '../data'
OUTPUT_FILE = '../aggregated_anova_data.csv'

MAIN_STUDY_COLS = [
    'participant_id', 'condition', 'trustworthiness', 'accuracy',
    'completeness', 'usefulness', 'comprehensibility'
]
PRE_STUDY_COLS_MAP = {
    'participant_id': 'participant_id',
    'demographics_age': 'age',
    'demographics_gender': 'gender',
    'demographics_education': 'education',
    'aiExperience_frequency': 'pre_aiFrequency',
    'aiTrust_generalTrust': 'pre_generalTrust'
}
POST_STUDY_COLS_MAP = {
    'participant_id': 'participant_id',
    'trustChange_generalTrust': 'post_generalTrust',
    'aiPerception_trustworthiness': 'post_overall_trustworthiness',
    'aiPerception_credibility': 'post_overall_credibility',
    'userExperience_usabilityFrustration': 'post_interaction_pleasantness'
}
FINAL_COLUMN_ORDER = [
    'participant_id', 'latency', 'complexity', 'trustworthiness', 'accuracy',
    'completeness', 'usefulness', 'comprehensibility', 'age', 'gender',
    'education', 'pre_aiFrequency', 'pre_generalTrust', 'post_generalTrust',
    'post_overall_trustworthiness', 'post_overall_credibility', 'post_interaction_pleasantness'
]

# --- Helper Functions ---
def print_header(title):
    print("\n" + "="*60 + f"\n--- {title} ---\n" + "="*60 + "\n")

def parse_condition(condition_string):
    try:
        parts = condition_string.split('_')
        if len(parts) == 2:
            return parts[0].capitalize(), parts[1].capitalize()
        return None, None
    except Exception:
        return None, None

# --- Main Script Logic ---
def main():
    print_header("Aggregating Participant Data")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_root_path = os.path.abspath(os.path.join(script_dir, PARTICIPANT_DATA_DIR))
    output_file_path = os.path.abspath(os.path.join(script_dir, OUTPUT_FILE))

    if not os.path.isdir(data_root_path):
        print(f"Error: Directory not found: '{data_root_path}'", file=sys.stderr)
        sys.exit(1)

    participant_dir_names = [
        d for d in os.listdir(data_root_path)
        if os.path.isdir(os.path.join(data_root_path, d)) and '-' in d and len(d) > 30
    ]

    if not participant_dir_names:
        print(f"No participant directories found in '{data_root_path}'.", file=sys.stderr)
        sys.exit(0)

    print(f"Found {len(participant_dir_names)} participant directories.")

    all_participant_data = []
    participants_processed = 0
    participants_skipped = 0

    for participant_id in participant_dir_names:
        p_dir_path = os.path.join(data_root_path, participant_id)
        main_study_file = os.path.join(p_dir_path, 'main_study_conditions.csv')
        pre_study_file = os.path.join(p_dir_path, 'pre_study.csv')
        post_study_file = os.path.join(p_dir_path, 'post_study.csv')

        if not (os.path.isfile(main_study_file) and os.path.isfile(pre_study_file) and os.path.isfile(post_study_file)):
            print(f"  Warning: Missing required CSV(s) for {participant_id}. Skipping.")
            participants_skipped += 1
            continue

        try:
            df_main = pd.read_csv(main_study_file, usecols=lambda c: c in MAIN_STUDY_COLS)
            df_pre = pd.read_csv(pre_study_file)
            df_post = pd.read_csv(post_study_file)

            if 'participant_id' not in df_main.columns or \
               'participant_id' not in df_pre.columns or \
               'participant_id' not in df_post.columns:
                 print(f"  Error: participant_id missing in CSVs for {participant_id}. Skipping.")
                 participants_skipped += 1
                 continue

            existing_pre_cols = {
                orig: new for orig, new in PRE_STUDY_COLS_MAP.items() if orig in df_pre.columns
            }
            if 'participant_id' not in existing_pre_cols and 'participant_id' in df_pre.columns:
                existing_pre_cols['participant_id'] = 'participant_id' # Ensure ID included for merge

            existing_post_cols = {
                orig: new for orig, new in POST_STUDY_COLS_MAP.items() if orig in df_post.columns
            }
            if 'participant_id' not in existing_post_cols and 'participant_id' in df_post.columns:
                existing_post_cols['participant_id'] = 'participant_id' # Ensure ID included for merge

            if not existing_pre_cols or not existing_post_cols:
                 print(f"  Error: Missing required pre/post study columns for {participant_id}. Skipping.")
                 participants_skipped += 1
                 continue

            df_pre_selected = df_pre[list(existing_pre_cols.keys())].iloc[[0]].copy()
            df_pre_selected.rename(columns=existing_pre_cols, inplace=True)

            df_post_selected = df_post[list(existing_post_cols.keys())].iloc[[0]].copy()
            df_post_selected.rename(columns=existing_post_cols, inplace=True)

            df_main['participant_id'] = df_main['participant_id'].astype(str)
            df_pre_selected['participant_id'] = df_pre_selected['participant_id'].astype(str)
            df_post_selected['participant_id'] = df_post_selected['participant_id'].astype(str)

            df_merged = pd.merge(df_main, df_pre_selected, on='participant_id', how='left')
            df_merged = pd.merge(df_merged, df_post_selected, on='participant_id', how='left')

            all_participant_data.append(df_merged)
            participants_processed += 1

        except Exception as e:
            print(f"  Error processing data for {participant_id}: {type(e).__name__} - {e}")
            participants_skipped += 1

    if not all_participant_data:
        print("\nError: No valid participant data aggregated.", file=sys.stderr)
        sys.exit(1)

    df_aggregated = pd.concat(all_participant_data, ignore_index=True)
    print(f"\nProcessed {participants_processed} participants successfully.")
    if participants_skipped > 0:
        print(f"Skipped {participants_skipped} participants due to errors.")

    print_header("Transforming Aggregated Data")

    parsed_conditions = df_aggregated['condition'].apply(parse_condition)
    df_aggregated['latency'] = parsed_conditions.apply(lambda x: x[0])
    df_aggregated['complexity'] = parsed_conditions.apply(lambda x: x[1])

    df_aggregated['latency'] = pd.Categorical(df_aggregated['latency'])
    df_aggregated['complexity'] = pd.Categorical(df_aggregated['complexity'])
    if 'gender' in df_aggregated.columns:
        df_aggregated['gender'] = df_aggregated['gender'].astype('category')
    if 'education' in df_aggregated.columns:
        df_aggregated['education'] = df_aggregated['education'].astype('category')
    if 'pre_aiFrequency' in df_aggregated.columns:
        df_aggregated['pre_aiFrequency'] = df_aggregated['pre_aiFrequency'].astype('category')

    numeric_cols = [
        'trustworthiness', 'accuracy', 'completeness', 'usefulness',
        'comprehensibility', 'age', 'pre_generalTrust', 'post_generalTrust',
        'post_overall_trustworthiness', 'post_overall_credibility', 'post_interaction_pleasantness'
    ]
    for col in numeric_cols:
        if col in df_aggregated.columns:
             df_aggregated[col] = pd.to_numeric(df_aggregated[col], errors='coerce')

    final_columns_present = [col for col in FINAL_COLUMN_ORDER if col in df_aggregated.columns]
    extra_cols = [col for col in df_aggregated.columns if col not in final_columns_present]
    df_final = df_aggregated[final_columns_present + extra_cols]

    print(f"Final data shape: {df_final.shape}")
    missing_final = df_final[FINAL_COLUMN_ORDER].isnull().sum()
    if missing_final.sum() > 0:
        print("\nWarning: Missing values detected in final aggregated data:")
        print(missing_final[missing_final > 0])
    else:
        print("No missing values detected in final core columns.")

    try:
        df_final.to_csv(output_file_path, index=False, encoding='utf-8')
        print(f"\nAggregated data saved to: {output_file_path}")
    except Exception as e:
        print(f"\nError saving data: {e}", file=sys.stderr)
        sys.exit(1)

    print("\nAggregation script finished.")


if __name__ == "__main__":
    main() 