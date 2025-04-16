#!/bin/bash

# Image Cleanup Script
# This script ensures proper management of ImgBB images and local cache files

# Activate virtual environment
source /home/study-project/gradio_app/venv/bin/activate

cd /home/study-project

python3 cleanup_images.py >> /home/study-project/logs/image_cleanup.log 2>&1

deactivate 