# Script: study-project/results/scripts/main_analysis/posthoc_comprehensibility.py
# Performs post-hoc pairwise comparisons for the significant interaction
# that we found in the 'comprehensibility' ANOVA.

import pandas as pd
import pingouin as pg
import os
import sys

# --- Configuration ---
AGGREGATED_DATA_FILE = '../../aggregated_anova_data.csv'
OUTPUT_DIR = '../../analysis_output'

SUBJECT_ID = 'participant_id'
WITHIN_VARS = ['latency', 'complexity']
DV = 'comprehensibility'

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
    print_header(f"Post-Hoc Tests for Interaction: {DV}")

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

    # --- 2. Perform Pairwise Tests ---
    print(f"\nRunning pairwise t-tests for '{DV}' across conditions...")
    print("Applying Bonferroni correction for multiple comparisons.")

    try:
        posthocs = pg.pairwise_tests(data=df, dv=DV, within=WITHIN_VARS,
                                     subject=SUBJECT_ID, padjust='bonf',
                                     effsize='cohen')

        print("\nPost-Hoc Test Results (Bonferroni Corrected):\n")
        print(posthocs[['Contrast', 'A', 'B', 'Paired', 'Parametric', 'T', 'dof', 'alternative', 'p-unc', 'p-corr', 'p-adjust', 'BF10', 'cohen']])

    except Exception as e:
        print(f"Error performing post-hoc tests: {e}", file=sys.stderr)
        sys.exit(1)

    print("\nPost-hoc analysis finished.")


if __name__ == "__main__":
    main() 