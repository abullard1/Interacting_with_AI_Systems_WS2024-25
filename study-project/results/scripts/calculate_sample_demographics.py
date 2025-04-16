# Script: study-project/results/scripts/calculate_sample_demographics.py

import pandas as pd
import os
import sys
import numpy as np

# --- Configuration ---
AGGREGATED_DATA_FILE = '../aggregated_anova_data.csv'
ID_COLUMN = 'participant_id'
AGE_COLUMN = 'age'
GENDER_COLUMN = 'gender'

# --- Helper Functions ---
def print_header(title):
    print("\n" + "="*60 + f"\n--- {title} ---\n" + "="*60 + "\n")

# --- Main Script Logic ---
def main():
    print_header("Final Analysis Sample Demographics")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_file_path = os.path.abspath(os.path.join(script_dir, AGGREGATED_DATA_FILE))

    if not os.path.isfile(data_file_path):
        print(f"Error: File not found: '{data_file_path}'", file=sys.stderr)
        sys.exit(1)

    try:
        df_aggregated = pd.read_csv(data_file_path)
        print(f"Loaded: {data_file_path}")
    except Exception as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        sys.exit(1)

    # --- Participant Count ---
    unique_participants = df_aggregated[ID_COLUMN].unique()
    final_sample_size = len(unique_participants)
    print(f"\nFinal Analysis Sample Size (N): {final_sample_size}")

    df_demographics = df_aggregated.drop_duplicates(subset=[ID_COLUMN]).copy()

    # --- Age Analysis ---
    print_header("Age Demographics")
    if AGE_COLUMN not in df_demographics.columns:
        print(f"Error: Age column '{AGE_COLUMN}' not found.")
    else:
        age_data = pd.to_numeric(df_demographics[AGE_COLUMN], errors='coerce').dropna()
        num_valid_ages = len(age_data)
        if num_valid_ages != final_sample_size:
            print(f"(Based on {num_valid_ages} participants with valid age data)")

        if num_valid_ages > 0:
            mean_age, sd_age = age_data.mean(), age_data.std()
            median_age, min_age, max_age = age_data.median(), age_data.min(), age_data.max()

            print(f"Mean Age:   {mean_age:.2f} (SD = {sd_age:.2f})")
            print(f"Median Age: {median_age:.0f}")
            print(f"Age Range:  {min_age:.0f}-{max_age:.0f}")

            # Age Brackets
            bins = [18, 25, 35, 45, 55, 65, np.inf]
            labels = ['18-24', '25-34', '35-44', '45-54', '55-64', '65+']
            age_brackets = pd.cut(age_data, bins=bins, labels=labels, right=True, include_lowest=True)
            print("\nAge Bracket Counts:")
            print(age_brackets.value_counts().sort_index())
        else:
             print("No valid age data found for the final sample.")

    # --- Gender Analysis ---
    print_header("Gender Demographics")
    if GENDER_COLUMN not in df_demographics.columns:
         print(f"Error: Gender column '{GENDER_COLUMN}' not found.")
    else:
        gender_counts = df_demographics[GENDER_COLUMN].value_counts()
        gender_perc = df_demographics[GENDER_COLUMN].value_counts(normalize=True) * 100
        print("Gender Distribution (Counts & Percentages):")
        gender_summary = pd.DataFrame({'Count': gender_counts, 'Percentage': gender_perc.round(1)})
        print(gender_summary)

    print("\nDemographics calculation complete.")

if __name__ == "__main__":
    main() 