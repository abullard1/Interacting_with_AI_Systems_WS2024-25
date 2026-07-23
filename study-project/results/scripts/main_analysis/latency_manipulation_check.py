# Script: study-project/results/scripts/main_analysis/latency_manipulation_check.py
# Checks if the latency manipulation was successful by comparing recorded delays.

import pandas as pd
import os
import sys
from scipy import stats
import logging

# --- Configuration ---
AGGREGATED_DATA_FILE = '../../aggregated_anova_data.csv'
PARTICIPANT_DATA_DIR = '../../data'

SUBJECT_ID = 'participant_id'
LATENCY_FACTOR = 'latency'
CONDITION_COL = 'condition'
DELAY_COL = 'response_delay_seconds'

# --- Main Analysis Logic ---
def main():
    print("\n" + "="*60)
    print(f"--- Latency Manipulation Check ---")
    print("="*60 + "\n")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    aggregated_file_path = os.path.abspath(os.path.join(script_dir, AGGREGATED_DATA_FILE))
    participant_data_path = os.path.abspath(os.path.join(script_dir, PARTICIPANT_DATA_DIR))

    # --- 1. Load Aggregated Data ---
    try:
        df_aggregated = pd.read_csv(aggregated_file_path)
        logging.info(f"Loaded aggregated data from: {aggregated_file_path}")
        valid_participants = df_aggregated[SUBJECT_ID].unique().astype(str)
        logging.info(f"Found {len(valid_participants)} valid participants for analysis.")
    except FileNotFoundError:
        logging.error(f"Aggregated data file not found: '{aggregated_file_path}'")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Error reading aggregated file '{aggregated_file_path}': {e}")
        sys.exit(1)

    # --- 2. Read Individual Files ---
    all_delay_data = []
    participants_processed = 0
    participants_skipped = 0

    logging.info(f"Reading individual participant data from: {participant_data_path}")

    for participant_id in valid_participants:
        individual_file = os.path.join(participant_data_path, participant_id, 'main_study_conditions.csv')

        try:
            df_individual = pd.read_csv(individual_file)

            if not {CONDITION_COL, DELAY_COL}.issubset(df_individual.columns):
                 logging.warning(f"Missing '{DELAY_COL}' or '{CONDITION_COL}' in {individual_file}. Skipping participant {participant_id}.")
                 participants_skipped += 1
                 continue

            df_delay = df_individual[[CONDITION_COL, DELAY_COL]].copy()
            df_delay[SUBJECT_ID] = participant_id
            df_delay[DELAY_COL] = pd.to_numeric(df_delay[DELAY_COL], errors='coerce')
            df_delay.dropna(subset=[DELAY_COL], inplace=True)
            df_delay[CONDITION_COL] = df_delay[CONDITION_COL].astype(str)

            if not df_delay.empty:
                all_delay_data.append(df_delay)
                participants_processed += 1
            else:
                logging.warning(f"No valid numeric delay data found for participant {participant_id} after filtering.")
                participants_skipped += 1

        except FileNotFoundError:
            logging.warning(f"Missing main_study_conditions.csv for participant {participant_id}. Skipping.")
            participants_skipped += 1
        except Exception as e:
            logging.warning(f"Error processing file for {participant_id} ({individual_file}): {type(e).__name__} - {e}")
            participants_skipped += 1

    if not all_delay_data:
        logging.error("Could not read valid delay data for any participant.")
        sys.exit(1)

    df_delays_raw = pd.concat(all_delay_data, ignore_index=True)
    logging.info(f"Successfully processed delay data for {participants_processed} participants.")
    if participants_skipped > 0:
         logging.warning(f"Skipped {participants_skipped} participants due to missing files, columns, or invalid data.")


    # --- 3. Merge Delay Data with Latency Factor ---
    df_factors = df_aggregated[[SUBJECT_ID, CONDITION_COL, LATENCY_FACTOR]].drop_duplicates()
    df_factors[SUBJECT_ID] = df_factors[SUBJECT_ID].astype(str)
    df_factors[CONDITION_COL] = df_factors[CONDITION_COL].astype(str)

    df_check = pd.merge(df_delays_raw, df_factors, on=[SUBJECT_ID, CONDITION_COL], how='left')

    missing_latency = df_check[LATENCY_FACTOR].isnull()
    if missing_latency.any():
        num_missing = missing_latency.sum()
        logging.warning(f"{num_missing} delay entries could not be matched with a Latency condition ('Fast'/'Slow'). Check data consistency. Analyzing only matched rows.")
        df_check.dropna(subset=[LATENCY_FACTOR], inplace=True)

    if df_check.empty:
        logging.error("No data available after merging delays and latency conditions.")
        sys.exit(1)


    # --- 4. Perform T-test ---
    print("\n" + "="*60)
    print(f"--- T-test for Latency Manipulation Check ---")
    print("="*60 + "\n")

    delays_fast = df_check.loc[df_check[LATENCY_FACTOR] == 'Fast', DELAY_COL]
    delays_slow = df_check.loc[df_check[LATENCY_FACTOR] == 'Slow', DELAY_COL]

    if delays_fast.empty or delays_slow.empty:
        logging.error("No data found for one or both latency conditions ('Fast'/'Slow') after filtering.")
        sys.exit(1)

    mean_fast, sd_fast = delays_fast.mean(), delays_fast.std()
    mean_slow, sd_slow = delays_slow.mean(), delays_slow.std()
    n_fast, n_slow = len(delays_fast), len(delays_slow)

    print("Descriptive Statistics for Recorded Delays (seconds):")
    print(f"  Fast Condition (N={n_fast}): Mean = {mean_fast:.3f}, SD = {sd_fast:.3f}")
    print(f"  Slow Condition (N={n_slow}): Mean = {mean_slow:.3f}, SD = {sd_slow:.3f}")

    t_stat, p_value = stats.ttest_ind(delays_fast, delays_slow, equal_var=False, nan_policy='omit')

    print("\nIndependent Samples T-test Results (Welch's t-test):")
    print(f"  T-statistic = {t_stat:.4f}")
    print(f"  P-value = {p_value:.4f}")

    alpha = 0.05
    if p_value < alpha:
        print(f"\nConclusion: The difference in recorded delays between Fast and Slow conditions is statistically significant (p < {alpha:.3f}).")
        print("Latency manipulation appears successful.")
    else:
        print(f"\nConclusion: The difference in recorded delays between Fast and Slow conditions is NOT statistically significant (p >= {alpha:.3f}).")
        print("Latency manipulation check FAILED.")


    print("\nManipulation check finished.")


if __name__ == "__main__":
    main() 