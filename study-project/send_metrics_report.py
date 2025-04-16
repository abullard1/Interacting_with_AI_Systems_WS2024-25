#!/usr/bin/env python3

import os
import sys
import logging
from datetime import datetime
import dotenv

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

try:
    backend_env_path = os.path.join(script_dir, 'backend', '.env')
    if os.path.exists(backend_env_path):
        logging.info(f"Loading environment variables from {backend_env_path}")
        dotenv.load_dotenv(backend_env_path)
    else:
        logging.warning(f"Backend .env file not found at {backend_env_path}")
    
    if not os.getenv("IMGBB_API_KEY"):
        logging.warning("ImgBB API key not set or using placeholder value. "
                      "Charts will be generated but not uploaded.")
    
    from gradio_app.models.metrics_reporter import metrics_reporter
    from gradio_app.models.metrics_visualizer import metrics_visualizer
    from gradio_app.models.scenario import scenario_manager
    
    logging.info("Starting metrics report generation and sending")
    
    if metrics_visualizer:
        logging.info("Metrics visualizer initialized successfully")
        logging.info(f"Images will be cached in: {metrics_visualizer.cache_dir}")
    
    success = metrics_reporter.send_email_report()
    
    if success:
        logging.info("Metrics report sent successfully with visualizations")
    else:
        logging.warning("Failed to send metrics report")
    
except Exception as e:
    logging.error(f"Error during metrics reporting: {str(e)}")
    import traceback
    logging.error(traceback.format_exc())
    sys.exit(1)

sys.exit(0) 