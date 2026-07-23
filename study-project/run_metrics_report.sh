#!/bin/bash

# Metrics Report Generator with Visualizations
# This script runs the metrics report generator to collect study statistics,
# create visualizations, and send an email report.

# Activate virtual environment
source /home/study-project/gradio_app/venv/bin/activate

# Change to the correct directory
cd /home/study-project

# Run the metrics report script
python3 send_metrics_report.py

# Deactivate the virtual environment
deactivate 