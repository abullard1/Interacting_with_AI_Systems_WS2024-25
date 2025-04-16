import os
import sys
import glob
import logging
import shutil
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

script_dir = os.path.dirname(os.path.abspath(__file__))
feedback_dir = os.path.join(script_dir, "gradio_app", "feedback")
locks_dir = os.path.join(feedback_dir, "locks")

def backup_locks_directory():
    try:
        if not os.path.exists(locks_dir):
            logging.warning(f"Locks directory does not exist: {locks_dir}")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = f"{locks_dir}_backup_{timestamp}"
        
        shutil.copytree(locks_dir, backup_dir)
        logging.info(f"Created backup of locks directory at: {backup_dir}")
        
        return backup_dir
    except Exception as e:
        logging.error(f"Error creating backup: {str(e)}")
        return None

def clean_all_locks():
    try:
        if not os.path.exists(locks_dir):
            logging.warning(f"Locks directory does not exist: {locks_dir}")
            return 0
        
        # Find all lock files
        lock_files = glob.glob(os.path.join(locks_dir, "*.lock"))
        logging.info(f"Found {len(lock_files)} lock files to remove")
        
        for lock_file in lock_files:
            try:
                file_size = os.path.getsize(lock_file)
                mod_time = datetime.fromtimestamp(os.path.getmtime(lock_file))
                
                try:
                    with open(lock_file, 'r') as f:
                        content = f.read().strip()
                except Exception:
                    content = "[Could not read content]"
                
                logging.info(f"Lock file: {os.path.basename(lock_file)}, Size: {file_size} bytes, " 
                            f"Modified: {mod_time}, Content: {content}")
            except Exception as e:
                logging.error(f"Error getting info for {os.path.basename(lock_file)}: {str(e)}")
        
        for lock_file in lock_files:
            try:
                os.remove(lock_file)
            except Exception as e:
                logging.error(f"Error removing {os.path.basename(lock_file)}: {str(e)}")
        
        remaining = glob.glob(os.path.join(locks_dir, "*.lock"))
        logging.info(f"Removed {len(lock_files) - len(remaining)} lock files. {len(remaining)} remaining.")
        
        return len(lock_files) - len(remaining)
    except Exception as e:
        logging.error(f"Error during cleaning of lock files: {str(e)}")
        return 0

def backup_and_clean_abandoned_users():
    try:
        user_dirs = []
        for item in os.listdir(feedback_dir):
            item_path = os.path.join(feedback_dir, item)
            if os.path.isdir(item_path) and item != 'locks' and item != 'abandoned':
                user_dirs.append(item_path)
        
        logging.info(f"Found {len(user_dirs)} user directories")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = os.path.join(feedback_dir, f"abandoned_{timestamp}")
        os.makedirs(backup_dir, exist_ok=True)
        
        moved_count = 0
        for user_dir in user_dirs:
            user_id = os.path.basename(user_dir)
            try:
                feedback_files = [f for f in os.listdir(user_dir) 
                                 if os.path.isfile(os.path.join(user_dir, f)) and 
                                 f.startswith('feedback_')]
                
                if len(feedback_files) < 4:
                    user_backup_dir = os.path.join(backup_dir, user_id)
                    logging.info(f"Moving abandoned user {user_id} with {len(feedback_files)} feedback files to backup")
                    
                    shutil.move(user_dir, user_backup_dir)
                    moved_count += 1
            except Exception as e:
                logging.error(f"Error processing user directory {user_id}: {str(e)}")
        
        logging.info(f"Moved {moved_count} abandoned user directories to {backup_dir}")
        return moved_count
    except Exception as e:
        logging.error(f"Error during backup and cleanup of abandoned users: {str(e)}")
        return 0

if __name__ == "__main__":
    try:
        confirmation = input("This will remove ALL lock files and clean up abandoned user directories. Are you sure? (type 'yes' to confirm): ")
        if confirmation.lower() != 'yes':
            logging.info("Operation cancelled by user")
            sys.exit(0)
        
        backup_dir = backup_locks_directory()
        if backup_dir:
            logging.info(f"Backup created at {backup_dir}")
        
        removed_count = clean_all_locks()
        logging.info(f"Successfully removed {removed_count} lock files")
        
        moved_count = backup_and_clean_abandoned_users()
        logging.info(f"Successfully moved {moved_count} abandoned user directories")
        
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        sys.exit(1)
    
    logging.info("Cleanup completed successfully")
    sys.exit(0) 