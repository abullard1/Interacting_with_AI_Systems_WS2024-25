# Script: study-project/results/scripts/main_analysis/generate_plots.py
# Generates key visualizations for the ANOVA results.

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import sys

# --- Configuration ---
AGGREGATED_DATA_FILE = '../../aggregated_anova_data.csv'
OUTPUT_DIR = '../../analysis_output/plots'

SUBJECT_ID = 'participant_id'
WITHIN_VARS = ['latency', 'complexity']
DVS = ['trustworthiness', 'comprehensibility']

# Plotting style
sns.set_theme(style="whitegrid")
PLOT_CONTEXT = "paper"
PLOT_STYLE = "ticks"
PLOT_PALETTE = "colorblind"

# --- Helper Functions ---
def print_header(title):
    print("\n" + "="*60)
    print(f"--- {title} ---")
    print("="*60 + "\n")

def ensure_dir(directory_path):
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)
        print(f"Created plot output directory: {directory_path}")

# --- Plotting Functions ---

def plot_interaction(df, dv, subject, within, output_dir):
    print(f"Generating interaction plot for: {dv}")
    if len(within) != 2:
        print(f"  Warning: Interaction plot designed for 2 factors. Skipping {dv}.")
        return

    factor1, factor2 = within[0], within[1] # e.g., latency, complexity

    try:
        plt.figure(figsize=(6, 4))
        sns.pointplot(data=df, x=factor2, y=dv, hue=factor1,
                      markers=True, linestyles='-', dodge=True,
                      errorbar=('ci', 95), # Show 95% Confidence Intervals
                      capsize=.1, palette=PLOT_PALETTE)

        plt.title(f'Interaction Plot for {dv.capitalize()}', fontsize=12)
        plt.xlabel(factor2.capitalize(), fontsize=10)
        plt.ylabel(f'Mean {dv.capitalize()} Rating', fontsize=10)
        plt.legend(title=factor1.capitalize(), title_fontsize='10', fontsize='9')
        plt.tick_params(axis='both', which='major', labelsize=9)
        sns.despine()

        filename = os.path.join(output_dir, f'{dv}_interaction_plot.png')
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f"  Saved plot: {filename}")
        plt.close()

    except Exception as e:
        print(f"  Error generating interaction plot for {dv}: {e}", file=sys.stderr)


def plot_bars(df, dv, subject, within, output_dir):
    print(f"Generating bar plot for: {dv}")
    if len(within) != 2:
        print(f"  Warning: Bar plot designed for 2 factors. Skipping {dv}.")
        return

    factor1, factor2 = within[0], within[1] # e.g., latency, complexity

    try:
        plt.figure(figsize=(6, 4))
        sns.barplot(data=df, x=factor2, y=dv, hue=factor1,
                    errorbar=('ci', 95),
                    capsize=.1, palette=PLOT_PALETTE)

        y_label = f'Mean {dv.capitalize()} Rating'
        plot_title = f'Mean {dv.capitalize()} Ratings by Condition'

        if dv == 'trustworthiness':
            y_label = 'Mean Quality Rating'
            plot_title = 'Mean Quality Ratings by Condition'

        plt.title(plot_title, fontsize=12)
        plt.xlabel(factor2.capitalize(), fontsize=10)
        plt.ylabel(y_label, fontsize=10)
        plt.legend(title=factor1.capitalize(), title_fontsize='10', fontsize='9', loc='upper left')
        plt.tick_params(axis='both', which='major', labelsize=9)
        sns.despine()

        filename = os.path.join(output_dir, f'{dv}_means_barplot.png')
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f"  Saved plot: {filename}")
        plt.close()

    except Exception as e:
        print(f"  Error generating bar plot for {dv}: {e}", file=sys.stderr)


def plot_complexity_main_effect(df, dvs, complexity_col, output_dir):
    print(f"Generating complexity main effect plot across DVs: {', '.join(dvs)}")

    try:
        means = df.groupby(complexity_col, observed=False)[dvs].mean().reset_index()
        means_melted = pd.melt(means, id_vars=[complexity_col], var_name='Dependent Variable', value_name='Mean Rating')

        plt.figure(figsize=(8, 5))
        sns.barplot(data=means_melted, x='Dependent Variable', y='Mean Rating', hue=complexity_col,
                    palette=PLOT_PALETTE, errorbar=None)

        plt.title('Main Effect of Complexity Across Dependent Variables', fontsize=12)
        plt.xlabel('Dependent Variable', fontsize=10)
        plt.ylabel('Mean Rating (1-7)', fontsize=10)
        plt.xticks(rotation=15, ha='right', fontsize=9)
        plt.legend(title=complexity_col.capitalize(), title_fontsize='10', fontsize='9', loc='upper right')
        plt.ylim(bottom=0)
        plt.tight_layout()
        sns.despine()

        filename = os.path.join(output_dir, 'complexity_main_effect_across_dvs_barplot.png')
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f"  Saved plot: {filename}")
        plt.close()

    except Exception as e:
        print(f"  Error generating complexity main effect plot: {e}", file=sys.stderr)


# --- Main Logic ---
def main():
    print_header("Generating Analysis Plots")
    sns.set_theme(style=PLOT_STYLE, context=PLOT_CONTEXT, palette=PLOT_PALETTE)

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

    # --- 2. Generate Plots ---

    # Interaction plot specifically for comprehensibility (where interaction was significant)
    plot_interaction(df, 'comprehensibility', SUBJECT_ID, WITHIN_VARS, output_path)

    # Bar plot for primary DV: trustworthiness
    plot_bars(df, 'trustworthiness', SUBJECT_ID, WITHIN_VARS, output_path)

    # Optional: Add more plots here if needed, e.g., for completeness which had a huge main effect
    plot_bars(df, 'completeness', SUBJECT_ID, WITHIN_VARS, output_path)

    # Plot showing complexity main effect across all DVs
    all_dvs = ['trustworthiness', 'accuracy', 'completeness', 'usefulness', 'comprehensibility']
    plot_complexity_main_effect(df, all_dvs, 'complexity', output_path)

    print("\nPlot generation finished.")


if __name__ == "__main__":
    main() 