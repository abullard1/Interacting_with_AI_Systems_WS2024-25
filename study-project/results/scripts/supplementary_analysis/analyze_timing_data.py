# Script: study-project/results/scripts/supplementary_analysis/analyze_timing_data.py
# Analyzes supplementary timing data (submit-to-loading, loading-to-response)
# extracted from our Firestore database to check for anomalies or outliers.
# In essence, we want to ensure that our latency values that we defined
# are actually reflected in the users frontend experience.

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
import sys
import logging

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# --- Configuration ---
TIMING_DATA_CSV = '../../../firebase-administration-scripts/extracted_data/timing_data.csv'
OUTPUT_DIR = '../../analysis_output/supplementary_plots' # Output dir for plots
IQR_MULTIPLIER = 1.5

# --- Helper Functions ---
def identify_outliers(series, iqr_multiplier):
    if series.isnull().all():
        return pd.Series([False] * len(series), index=series.index)
    Q1 = series.quantile(0.25)
    Q3 = series.quantile(0.75)
    IQR = Q3 - Q1
    if IQR <= 0:
        return pd.Series([False] * len(series), index=series.index)
    lower_bound = Q1 - iqr_multiplier * IQR
    upper_bound = Q3 + iqr_multiplier * IQR
    is_outlier = ((series < lower_bound) | (series > upper_bound)) & series.notna()
    return is_outlier

# --- Main Analysis Logic ---
def main():
    print("\n" + "="*60)
    print(f"--- Supplementary Timing Data Analysis ---")
    print("="*60 + "\n")
    sns.set_theme(style="whitegrid")

    # --- 1. Load Data ---
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_file_path = os.path.abspath(os.path.join(script_dir, TIMING_DATA_CSV))
    output_path = os.path.abspath(os.path.join(script_dir, OUTPUT_DIR))

    try:
        os.makedirs(output_path, exist_ok=True)
        logging.info(f"Ensured plot output directory exists: {output_path}")
    except OSError as e:
        logging.error(f"Failed to create output directory '{output_path}': {e}")
        sys.exit(1)

    try:
        df = pd.read_csv(data_file_path)
        # Convert ms to seconds
        df['submit_vs_loading_s'] = df['submit_vs_loading_ms'] / 1000.0
        df['loading_to_response_s'] = df['loading_to_response_ms'] / 1000.0
        logging.info(f"Loaded timing data: {data_file_path} (Shape: {df.shape})")

        initial_rows = len(df)
        missing_submit_initial = df['submit_vs_loading_s'].isnull().sum()
        missing_load_initial = df['loading_to_response_s'].isnull().sum()
        logging.info(f"Initial missing values - submit_vs_loading_s: {missing_submit_initial}, loading_to_response_s: {missing_load_initial}")

        df.dropna(subset=['submit_vs_loading_s', 'loading_to_response_s'], how='all', inplace=True)
        rows_after_drop = len(df)
        logging.info(f"Shape after dropping rows with no timing data: {df.shape} (Removed {initial_rows - rows_after_drop} rows)")

    except FileNotFoundError:
        logging.error(f"Timing data CSV not found: '{data_file_path}'")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Error reading or processing file '{data_file_path}': {e}")
        sys.exit(1)

    if df.empty:
        logging.warning("No valid timing data rows remaining after cleaning. Exiting.")
        sys.exit(0)

    # --- 2. Descriptive Statistics (Overall) ---
    print("\n" + "="*60)
    print(f"--- Overall Descriptive Statistics (seconds) ---")
    print("="*60 + "\n")

    desc_submit = df['submit_vs_loading_s'].dropna().describe()
    desc_load = df['loading_to_response_s'].dropna().describe()

    print("Submit Button Click -> Loading Indicator Appearance (submit_vs_loading_s):")
    print(desc_submit.round(3))
    print("\nLoading Indicator Appearance -> First Response Word (loading_to_response_s):")
    print(desc_load.round(3))

    # --- 3. Outlier Analysis ---
    print("\n" + "="*60)
    print(f"--- Outlier Identification (IQR Multiplier = {IQR_MULTIPLIER}) ---")
    print("="*60 + "\n")

    df['is_outlier_submit'] = identify_outliers(df['submit_vs_loading_s'], IQR_MULTIPLIER)
    df['is_outlier_load'] = identify_outliers(df['loading_to_response_s'], IQR_MULTIPLIER)

    n_outliers_submit = df['is_outlier_submit'].sum()
    n_outliers_load = df['is_outlier_load'].sum()
    total_valid_submit = df['submit_vs_loading_s'].notna().sum()
    total_valid_load = df['loading_to_response_s'].notna().sum()

    if total_valid_submit > 0:
        perc_outliers_submit = (n_outliers_submit / total_valid_submit) * 100
        logging.info(f"Submit -> Loading Outliers: {n_outliers_submit} / {total_valid_submit} ({perc_outliers_submit:.1f}%)")
        if n_outliers_submit > 0:
            print("  Outlier values (s):", df.loc[df['is_outlier_submit'], 'submit_vs_loading_s'].round(3).tolist())
    else:
        logging.info("No valid data for Submit -> Loading timing.")

    if total_valid_load > 0:
        perc_outliers_load = (n_outliers_load / total_valid_load) * 100
        logging.info(f"Loading -> Response Outliers: {n_outliers_load} / {total_valid_load} ({perc_outliers_load:.1f}%)")
        if n_outliers_load > 0:
            print("  Outlier values (s):", df.loc[df['is_outlier_load'], 'loading_to_response_s'].round(3).tolist())
    else:
        logging.info("No valid data for Loading -> Response timing.")

    # --- 4. Visualizations ---
    print("\n" + "="*60)
    print(f"--- Generating Visualizations ---")
    print("="*60 + "\n")

    plot_configs = [
        {
            'column': 'submit_vs_loading_s',
            'title_hist': 'Distribution of Submit -> Loading Indicator Time',
            'title_box': 'Boxplot of Submit -> Loading Indicator Time',
            'filename_base': 'submit_vs_loading'
        },
        {
            'column': 'loading_to_response_s',
            'title_hist': 'Distribution of Loading Indicator -> First Response Word Time',
            'title_box': 'Boxplot of Loading Indicator -> First Response Word Time',
            'filename_base': 'loading_to_response'
        }
    ]

    for config in plot_configs:
        column = config['column']
        if column in df and df[column].notna().any():
            # Histogram
            plt.figure(figsize=(8, 4))
            sns.histplot(data=df, x=column, kde=False, bins=30)
            plt.title(config['title_hist'])
            plt.xlabel('Time (seconds)')
            plt.ylabel('Frequency')
            filename_hist = os.path.join(output_path, f"{config['filename_base']}_distribution.png")
            try:
                plt.savefig(filename_hist, dpi=300, bbox_inches='tight')
                logging.info(f"Saved plot: {filename_hist}")
            except Exception as e:
                 logging.warning(f"Could not save plot {filename_hist}: {e}")
            plt.close()

            # Boxplot
            plt.figure(figsize=(6, 4))
            sns.boxplot(data=df, y=column)
            plt.title(config['title_box'])
            plt.ylabel('Time (seconds)')
            filename_box = os.path.join(output_path, f"{config['filename_base']}_boxplot.png")
            try:
                plt.savefig(filename_box, dpi=300, bbox_inches='tight')
                logging.info(f"Saved plot: {filename_box}")
            except Exception as e:
                logging.warning(f"Could not save plot {filename_box}: {e}")
            plt.close()
        else:
            logging.warning(f"Skipping plots for '{column}' as it contains no valid data.")


    print("\nSupplementary timing analysis finished.")


if __name__ == "__main__":
    main()