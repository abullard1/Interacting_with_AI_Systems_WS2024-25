# Script: study-project/results/scripts/main_analysis/analyze_pre_post.py
# Analyzes demographic data and pre-post study changes (e.g., trust).

import pandas as pd
from scipy import stats
import os
import sys

# --- Configuration ---
AGGREGATED_DATA_FILE = '../../aggregated_anova_data.csv'
OUTPUT_DIR = '../../analysis_output'

PRE_STUDY_TRUST = 'pre_generalTrust'
POST_STUDY_TRUST = 'post_generalTrust'
AGE = 'age'
GENDER = 'gender'
EDUCATION = 'education'
AI_FREQUENCY = 'pre_aiFrequency'

POST_OVERALL_TRUST = 'post_overall_trustworthiness'
POST_OVERALL_CRED = 'post_overall_credibility'
POST_PLEASANTNESS = 'post_interaction_pleasantness'

# --- Helper Functions ---
def print_header(title):
    print("\n" + "="*60)
    print(f"--- {title} ---")
    print("="*60 + "\n")

def ensure_dir(directory_path):
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)

# --- Main Analysis Logic ---
def main():
    print_header("Pre/Post Study and Demographic Analysis")

    # --- 1. Load Data ---
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_file_path = os.path.abspath(os.path.join(script_dir, AGGREGATED_DATA_FILE))
    output_path = os.path.abspath(os.path.join(script_dir, OUTPUT_DIR))

    ensure_dir(output_path)

    if not os.path.isfile(data_file_path):
        print(f"Error: File not found: '{data_file_path}'", file=sys.stderr)
        sys.exit(1)

    try:
        df_full = pd.read_csv(data_file_path)
        df = df_full.drop_duplicates(subset=['participant_id']).reset_index(drop=True)
        print(f"Loaded and deduplicated data: {data_file_path} (Participants: {df.shape[0]})")
    except Exception as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        sys.exit(1)

    # --- 2. Demographic Analysis ---
    print_header("Demographic Summary")

    # Age
    if AGE in df.columns and pd.api.types.is_numeric_dtype(df[AGE]):
        print(f"Age: Mean = {df[AGE].mean():.2f}, SD = {df[AGE].std():.2f}, Min = {df[AGE].min()}, Max = {df[AGE].max()}")
    else:
        print(f"  Warning: Column '{AGE}' not found or not numeric.")

    # Gender
    if GENDER in df.columns:
        print("\nGender Distribution:")
        print(df[GENDER].value_counts(normalize=True).round(3) * 100) # Percentages
    else:
        print(f"  Warning: Column '{GENDER}' not found.")

    # Education
    if EDUCATION in df.columns:
        print("\nEducation Distribution:")
        print(df[EDUCATION].value_counts(normalize=True).round(3) * 100) # Percentages
    else:
        print(f"  Warning: Column '{EDUCATION}' not found.")
        
    # Pre-Study AI Frequency
    if AI_FREQUENCY in df.columns:
        print("\nPre-Study AI Usage Frequency:")
        print(df[AI_FREQUENCY].value_counts(normalize=True).round(3) * 100) # Percentages
    else:
        print(f"  Warning: Column '{AI_FREQUENCY}' not found.")

    # --- 3. Pre vs. Post Trust Analysis ---
    print_header("Pre vs. Post General Trust Analysis")

    # Check if columns exist and are numeric
    if PRE_STUDY_TRUST in df.columns and POST_STUDY_TRUST in df.columns and \
       pd.api.types.is_numeric_dtype(df[PRE_STUDY_TRUST]) and pd.api.types.is_numeric_dtype(df[POST_STUDY_TRUST]):

        # Drop rows with missing values in either column for the paired test
        trust_df = df[[PRE_STUDY_TRUST, POST_STUDY_TRUST]].dropna()
        n_pairs = len(trust_df)
        print(f"Performing paired t-test on {n_pairs} participants with complete trust data.")

        if n_pairs < 2:
            print("  Error: Not enough paired data points to perform t-test.", file=sys.stderr)
        else:
            try:
                t_statistic, p_value = stats.ttest_rel(trust_df[PRE_STUDY_TRUST], trust_df[POST_STUDY_TRUST])

                print(f"\nPre-Study Trust: Mean = {trust_df[PRE_STUDY_TRUST].mean():.2f}, SD = {trust_df[PRE_STUDY_TRUST].std():.2f}")
                print(f"Post-Study Trust: Mean = {trust_df[POST_STUDY_TRUST].mean():.2f}, SD = {trust_df[POST_STUDY_TRUST].std():.2f}")
                print(f"\nPaired Samples T-Test Result:")
                print(f"  t({n_pairs - 1}) = {t_statistic:.3f}")
                print(f"  p-value = {p_value:.3f}")

                if p_value < 0.05:
                    print("  Result: Significant difference between pre- and post-study trust.")
                    if trust_df[POST_STUDY_TRUST].mean() > trust_df[PRE_STUDY_TRUST].mean():
                         print("  Interpretation: General trust in AI significantly increased after the study.")
                    else:
                         print("  Interpretation: General trust in AI significantly decreased after the study.")
                else:
                    print("  Result: No significant difference between pre- and post-study trust.")

            except Exception as e:
                print(f"  Error performing paired t-test: {e}", file=sys.stderr)
    else:
        print(f"  Warning: Columns '{PRE_STUDY_TRUST}' or '{POST_STUDY_TRUST}' not found or not numeric. Skipping t-test.")

    # --- 4. Post-Study Overall Ratings --- 
    print_header("Post-Study Overall Perception Ratings")

    post_cols_to_analyze = {
        POST_OVERALL_TRUST: "Overall Trustworthiness",
        POST_OVERALL_CRED: "Overall Credibility",
        POST_PLEASANTNESS: "Interaction Pleasantness"
    }

    for col, name in post_cols_to_analyze.items():
        if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
            mean_val = df[col].mean()
            sd_val = df[col].std()
            print(f"{name}: Mean = {mean_val:.2f}, SD = {sd_val:.2f}")
        else:
            print(f"  Warning: Column '{col}' ('{name}') not found or not numeric.")

    print("\nPre/Post analysis finished.")


if __name__ == "__main__":
    main() 