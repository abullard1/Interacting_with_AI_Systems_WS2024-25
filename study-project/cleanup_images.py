import os
import sys
import logging
from datetime import datetime
import dotenv
import shutil
import base64
import requests
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

def load_environment():
    backend_env_path = os.path.join(script_dir, 'backend', '.env')
    if os.path.exists(backend_env_path):
        logging.info(f"Loading environment variables from {backend_env_path}")
        dotenv.load_dotenv(backend_env_path)
    else:
        logging.warning(f"Backend .env file not found at {backend_env_path}")

def cleanup_local_cache(cache_dir, max_age_days=7):
    if not os.path.exists(cache_dir):
        logging.warning(f"Cache directory {cache_dir} does not exist")
        return 0
    
    try:
        now = datetime.now()
        count = 0
        
        essential_charts = [
            "completion_chart.png",
            "scenario_chart.png",
            "design_chart.png"
        ]
        
        logging.info(f"Cleaning up cache directory: {cache_dir}")
        logging.info(f"Essential charts that will be preserved: {essential_charts}")
        
        for file_name in os.listdir(cache_dir):
            file_path = os.path.join(cache_dir, file_name)
            
            if not os.path.isfile(file_path):
                continue
                
            if file_name in essential_charts:
                logging.info(f"Keeping essential chart: {file_name}")
                continue
            
            mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
            age_days = (now - mtime).days
            
            if age_days > max_age_days or (not file_name in essential_charts and "_" in file_name):
                os.remove(file_path)
                count += 1
                logging.info(f"Deleted cache file: {file_name} (age: {age_days} days)")
        
        return count
        
    except Exception as e:
        logging.error(f"Error cleaning up cache files: {str(e)}")
        return 0

def reupload_essential_charts(cache_dir):
    imgbb_api_key = os.getenv("IMGBB_API_KEY")
    if not imgbb_api_key:
        logging.error("ImgBB API key not configured. Cannot upload images.")
        return
    
    essential_charts = [
        "completion_chart.png",
        "scenario_chart.png",
        "design_chart.png"
    ]
    
    expiration = 7 * 24 * 60 * 60  # 7 days in seconds
    
    for chart_name in essential_charts:
        image_path = os.path.join(cache_dir, chart_name)
        if not os.path.exists(image_path):
            logging.warning(f"Chart file not found: {image_path}")
            continue
        
        try:
            with open(image_path, "rb") as file:
                image_data = base64.b64encode(file.read())
            
            url = "https://api.imgbb.com/1/upload"
            payload = {
                "key": imgbb_api_key,
                "image": image_data,
                "name": chart_name.replace(".png", ""),
                "expiration": expiration
            }
            
            logging.info(f"Reuploading essential chart: {chart_name}")
            response = requests.post(url, payload)
            
            if response.status_code == 200:
                json_data = response.json()
                if json_data.get("success", False):
                    image_url = json_data["data"]["url"]
                    delete_url = json_data["data"].get("delete_url", "Not available")
                    logging.info(f"Successfully uploaded image: {chart_name}")
                    logging.info(f"Image URL: {image_url}")
                    logging.info(f"Delete URL: {delete_url}")
                else:
                    logging.error(f"Failed to upload image: {json_data.get('error', {}).get('message', 'Unknown error')}")
            else:
                logging.error(f"Failed to upload image. Status code: {response.status_code}")
        
        except Exception as e:
            logging.error(f"Error uploading image to ImgBB: {str(e)}")

def main():
    logging.info("Starting image cleanup process")
    
    load_environment()
    
    cache_dir = os.path.join(script_dir, "logs", "metrics_images")
    logging.info(f"Cache directory: {cache_dir}")
    
    deleted_count = cleanup_local_cache(cache_dir)
    logging.info(f"Deleted {deleted_count} files from local cache")
    
    reupload_essential_charts(cache_dir)
    
    logging.info("Image cleanup process completed")

if __name__ == "__main__":
    main() 