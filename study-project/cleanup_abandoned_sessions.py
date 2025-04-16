import os
import sys
import logging
import glob
import time
import argparse
from datetime import datetime, timedelta

def parse_args():
    parser = argparse.ArgumentParser(description='Clean up abandoned sessions and optionally specific users')
    parser.add_argument('--user', help='Specific user ID to clean up')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    return parser.parse_args()

args = parse_args()
logging.basicConfig(
    level=logging.DEBUG if args.verbose else logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

def cleanup_stale_lock_files(lock_dir, stale_hours=1.0):
    if not os.path.exists(lock_dir):
        logging.warning(f"Lock directory does not exist: {lock_dir}")
        return
    
    try:
        now = time.time()
        stale_threshold = now - (stale_hours * 3600)
        current_time = datetime.now()
        
        lock_files = glob.glob(os.path.join(lock_dir, "*.lock"))
        logging.info(f"Found {len(lock_files)} lock files")
        
        removed_count = 0
        for lock_file in lock_files:
            try:
                mtime = os.path.getmtime(lock_file)
                
                is_stale_by_content = False
                try:
                    with open(lock_file, 'r') as f:
                        content = f.read().strip()
                    
                    if ':' in content:
                        parts = content.split(':', 1)
                        if len(parts) >= 2:
                            timestamp_str = parts[1].split('T')[0]
                            try:
                                today_str = current_time.strftime('%Y-%m-%d')
                                is_stale_by_content = timestamp_str != today_str
                            except Exception:
                                pass
                
                except Exception as e:
                    logging.error(f"Error reading lock file content: {str(e)}")
                
                if mtime < stale_threshold or is_stale_by_content:
                    try:
                        with open(lock_file, 'r') as f:
                            content = f.read().strip()
                        logging.info(f"Removing stale lock file: {os.path.basename(lock_file)}, content: {content}, age: {(now - mtime) / 3600:.2f} hours, stale by content: {is_stale_by_content}")
                    except Exception as e:
                        logging.error(f"Error reading lock file before removal: {str(e)}")
                    
                    os.remove(lock_file)
                    removed_count += 1
                else:
                    logging.info(f"Keeping non-stale lock file: {os.path.basename(lock_file)}, age: {(now - mtime) / 3600:.2f} hours")
            except Exception as e:
                logging.error(f"Error processing lock file {os.path.basename(lock_file)}: {str(e)}")
        
        logging.info(f"Removed {removed_count} stale lock files")
    except Exception as e:
        logging.error(f"Error during lock file cleanup: {str(e)}")

try:
    args = parse_args()
    
    try:
        logging.info("Initializing task_distributor")
        
        try:
            from gradio_app.models.selection_algorithm import task_distributor
            if task_distributor is None:
                raise ImportError("task_distributor is None")
        except (ImportError, AttributeError):
            logging.info("Initializing TaskDistributor via ScenarioManager")
            from gradio_app.models.scenario import ScenarioManager
            temp_manager = ScenarioManager()
            from gradio_app.models.selection_algorithm import task_distributor

        feedback_dir = task_distributor.feedback_dir
        logging.info(f"Feedback directory: {feedback_dir}")
        if os.path.exists(feedback_dir):
            user_dirs = [d for d in os.listdir(feedback_dir) 
                        if os.path.isdir(os.path.join(feedback_dir, d))
                        and d not in {'locks', 'abandoned'}]
            logging.info(f"User directories found: {user_dirs}")
            
            for test_user in ["test_under_hour", "test_over_hour"]:
                if test_user in user_dirs:
                    test_user_path = os.path.join(feedback_dir, test_user)
                    mtime = os.path.getmtime(test_user_path)
                    age_minutes = (time.time() - mtime) / 60
                    age_hours = age_minutes / 60
                    logging.info(f"Test user {test_user} directory age: {age_minutes:.2f} minutes ({age_hours:.2f} hours)")
                    
                    if age_minutes > 60:
                        logging.info(f"Test user {test_user} should be abandoned (age > 60 minutes)")
                    else:
                        logging.info(f"Test user {test_user} not abandoned yet (age <= 60 minutes)")
        
        if args.user:
            user_id = args.user
            logging.info(f"Cleaning up specific user: {user_id}")
            result = task_distributor.cleanup_user_data(user_id)
            if result:
                logging.info(f"Successfully cleaned up user {user_id}")
            else:
                logging.error(f"Failed to clean up user {user_id}")
        else:
            logging.info("Running regular abandoned session cleanup")
            task_distributor.cleanup_abandoned_sessions()
            logging.info("Task distributor cleanup completed successfully")
    except Exception as e:
        logging.error(f"Error during task_distributor operations: {str(e)}")
    
    logging.info("Starting direct cleanup of stale lock files")
    feedback_dir = os.path.join(script_dir, "gradio_app", "feedback")
    lock_dir = os.path.join(feedback_dir, "locks")
    
    cleanup_stale_lock_files(lock_dir, stale_hours=1.0)
    
    logging.info("Direct lock file cleanup completed successfully")

except Exception as e:
    logging.error(f"Error during cleanup: {str(e)}")
    sys.exit(1)

logging.info("All cleanup operations completed")
sys.exit(0) 