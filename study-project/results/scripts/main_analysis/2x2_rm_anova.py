# Script: study-project/results/scripts/main_analysis/2x2_rm_anova.py
# Performs 2x2 Repeated Measures ANOVAs on study data for multiple DVs.

import pandas as pd
from statsmodels.stats.anova import AnovaRM
from scipy import stats
import os
import sys

# --- Configuration ---
AGGREGATED_DATA_FILE = '../../aggregated_anova_data.csv'
OUTPUT_DIR = '../../analysis_output'

SUBJECT_ID = 'participant_id'
WITHIN_VARS = ['latency', 'complexity']

DVS_TO_ANALYZE = [
    'trustworthiness',
    'accuracy',
    'completeness',
    'usefulness',
    'comprehensibility'
]

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
    print_header("2x2 RM ANOVA Analysis for All Dependent Variables")

    # --- 1. Load Data ---
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_file_path = os.path.abspath(os.path.join(script_dir, AGGREGATED_DATA_FILE))
    output_path = os.path.abspath(os.path.join(script_dir, OUTPUT_DIR))

    ensure_dir(output_path)

    if not os.path.isfile(data_file_path):
        print(f"Error: File not found: '{data_file_path}'", file=sys.stderr)
        sys.exit(1)

    try:
        df = pd.read_csv(data_file_path)
        print(f"Loaded data: {data_file_path} (Shape: {df.shape})")
    except Exception as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        sys.exit(1)

    # --- 2.  ---
    for current_dv in DVS_TO_ANALYZE:
        print_header(f"Analysis for Dependent Variable: {current_dv}")

        if current_dv not in df.columns:
            print(f"  Warning: Dependent variable '{current_dv}' not found in data. Skipping.")
            continue

        key_cols_to_check = [SUBJECT_ID, current_dv] + WITHIN_VARS
        missing_values_count = df[key_cols_to_check].isnull().sum().sum()
        if missing_values_count > 0:
            print(f"  Warning: Found {missing_values_count} missing values in critical columns for {current_dv}. Skipping ANOVA for this DV.", file=sys.stderr)
            continue
        else:
            print("  Data integrity check passed.")

        # --- 2a. Descriptive Statistics --- 
        print(f"\n  Calculating Descriptive Statistics for: {current_dv}")
        try:
            descriptives = df.groupby(WITHIN_VARS, observed=False)[current_dv].agg(['mean', 'std', 'count']).round(3)
            print("  Means, Standard Deviations, and Counts per Condition:\n")
            print(descriptives)
        except Exception as e:
            print(f"  Error calculating descriptives for {current_dv}: {e}", file=sys.stderr)

        # --- 2b. Normality Check (Shapiro-Wilk per condition) --- 
        print(f"\n  Checking Normality (Shapiro-Wilk) for: {current_dv} within each condition...")
        normality_results = {}
        try:
            grouped = df.groupby(WITHIN_VARS, observed=False)
            for name, group in grouped:
                condition_name = '_'.join(name)
                if len(group[current_dv].dropna()) > 3:
                    stat, p_value = stats.shapiro(group[current_dv].dropna())
                    normality_results[condition_name] = {'W': stat, 'p_value': p_value}
                    print(f"    Condition: {condition_name}, W = {stat:.3f}, p = {p_value:.3f}{' (Potential Violation)' if p_value < 0.05 else ''}")
                else:
                     print(f"    Condition: {condition_name}, Skipped (<=3 data points)")
                     normality_results[condition_name] = {'W': pd.NA, 'p_value': pd.NA}
        except Exception as e:
             print(f"  Error performing normality checks for {current_dv}: {e}", file=sys.stderr)

        # --- 2c. RM ANOVA --- 
        print(f"\n  Running 2x2 RM ANOVA (Latency x Complexity) on '{current_dv}'...")
        try:
            aov = AnovaRM(data=df,
                          depvar=current_dv,
                          subject=SUBJECT_ID,
                          within=WITHIN_VARS)
            results = aov.fit()

            # Calculates the Partial Eta-Squared using F and df
            anova_table = results.anova_table
            try:
                df_error = anova_table['Den DF'].iloc[-1]
            except (IndexError, KeyError):
                df_error = pd.NA

            if pd.notna(df_error):
                anova_table['eta-sq-part'] = (anova_table['F Value'] * anova_table['Num DF']) / \
                                            (anova_table['F Value'] * anova_table['Num DF'] + df_error)
            else:
                anova_table['eta-sq-part'] = pd.NA
                print("  Warning: Could not determine Denominator DF for effect size calculation.")

            anova_table.rename(columns={'F Value': 'F', 'Pr > F': 'p-value'}, inplace=True)

            print("\n  ANOVA Results Table (with Partial Eta-Squared):\n")
            display_cols = ['F', 'Num DF', 'Den DF', 'p-value', 'eta-sq-part']
            print(anova_table[display_cols].round({'F': 2, 'p-value': 3, 'eta-sq-part': 3}))

        except Exception as e:
            print(f"  Error performing RM ANOVA for {current_dv}: {e}", file=sys.stderr)


    print("\nAnalysis script finished for all specified DVs.")


if __name__ == "__main__":
    main() 