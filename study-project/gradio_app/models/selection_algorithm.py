import os
import json
import time
import random
import threading
import fcntl
import glob
from datetime import datetime, timedelta

from gradio_app.utils.logger import log_print

class TaskDistributor:
    """
    Handles the distribution of scenarios and conditions to participants
    in a balanced way, ensuring that each participant sees each scenario
    exactly once and is exposed to all conditions in a balanced manner.
    
    This class also handles marking scenarios as in-progress to prevent
    concurrent access, and cleaning up abandoned sessions.
    """
    
    def __init__(self, scenarios_dir, feedback_dir):
        self.scenarios_dir = scenarios_dir
        self.feedback_dir = feedback_dir
        
        self.user_completions = {}
        
        self.in_progress_scenarios = {}
        
        self.global_completions = {}
        self.max_scenarios_per_user = 4
        
        self.timeout_minutes = 60
        
        self.lock_file_base = os.path.join(feedback_dir, "locks")
        os.makedirs(self.lock_file_base, exist_ok=True)
        
        self.state_lock = threading.RLock()
        
        self._initialize_completion_tracking()
        
        log_print("TaskDistributor initialized")
    
    def _initialize_completion_tracking(self):
        with self.state_lock:
            if not os.path.exists(self.feedback_dir):
                log_print("Feedback directory doesn't exist, creating it")
                os.makedirs(self.feedback_dir, exist_ok=True)
                return
            
            for user_id in os.listdir(self.feedback_dir):
                user_dir = os.path.join(self.feedback_dir, user_id)
                if not os.path.isdir(user_dir) or user_id == "locks":
                    continue
                    
                self.user_completions[user_id] = []
                
                for feedback_file in os.listdir(user_dir):
                    if not feedback_file.endswith('.json'):
                        continue
                        
                    feedback_path = os.path.join(user_dir, feedback_file)
                    try:
                        with open(feedback_path, 'r', encoding='utf-8') as f:
                            feedback_data = json.load(f)
                        
                        scenario_id = feedback_data.get('scenario_id')
                        condition = feedback_data.get('condition')
                        
                        if scenario_id and condition:
                            scenario_condition_key = f"{scenario_id}_{condition}"
                            
                            if scenario_condition_key not in self.user_completions[user_id]:
                                self.user_completions[user_id].append(scenario_condition_key)
                            
                            self.global_completions[scenario_condition_key] = self.global_completions.get(scenario_condition_key, 0) + 1
                    except Exception as e:
                        log_print(f"Error reading feedback file {feedback_path}: {str(e)}")
            
            log_print(f"Initialized with {len(self.user_completions)} users and {len(self.global_completions)} scenario-condition completions")
    
    def get_available_scenarios(self):
        if not os.path.exists(self.scenarios_dir):
            log_print(f"Scenarios directory not found: {self.scenarios_dir}")
            return []
            
        return [
            folder for folder in os.listdir(self.scenarios_dir) 
            if os.path.isdir(os.path.join(self.scenarios_dir, folder))
        ]
    
    def get_available_conditions(self, scenario_id):
        scenario_path = os.path.join(self.scenarios_dir, scenario_id)
        if not os.path.exists(scenario_path):
            log_print(f"Scenario directory not found: {scenario_path}")
            return []
            
        return [
            folder for folder in os.listdir(scenario_path) 
            if os.path.isdir(os.path.join(scenario_path, folder))
        ]
    
    def cleanup_abandoned_sessions(self):
        with self.state_lock:
            current_time = datetime.now()
            timeout_threshold = timedelta(minutes=self.timeout_minutes)
            
            keys_to_remove = []
            
            abandoned_users = set()
            
            for scenario_condition_key, info in self.in_progress_scenarios.items():
                timestamp = info.get("timestamp")
                user_id = info.get("user_id")
                
                if timestamp and (current_time - timestamp) > timeout_threshold:
                    log_print(f"Cleaning up abandoned scenario: {scenario_condition_key} for user {user_id}")
                    keys_to_remove.append(scenario_condition_key)
                    
                    if user_id:
                        abandoned_users.add(user_id)
            
            for key in keys_to_remove:
                if 'lock_handle' in self.in_progress_scenarios[key]:
                    try:
                        self.in_progress_scenarios[key]['lock_handle'].close()
                    except Exception as e:
                        log_print(f"Error closing lock file handle during cleanup: {str(e)}")
                
                del self.in_progress_scenarios[key]
                
                self._release_file_lock(key)
            
            if keys_to_remove:
                log_print(f"Cleaned up {len(keys_to_remove)} abandoned scenarios")
                
            try:
                file_age_threshold = timedelta(minutes=60)
                
                special_dirs = {'locks', 'abandoned'}
                user_dirs = [d for d in os.listdir(self.feedback_dir) 
                            if os.path.isdir(os.path.join(self.feedback_dir, d))
                            and d not in special_dirs]
                
                for user_dir_name in user_dirs:
                    user_dir_path = os.path.join(self.feedback_dir, user_dir_name)
                    
                    try:
                        dir_mtime = os.path.getmtime(user_dir_path)
                        dir_age = datetime.now() - datetime.fromtimestamp(dir_mtime)
                        
                        if dir_age > file_age_threshold:
                            log_print(f"Found abandoned user directory: {user_dir_name}, age: {dir_age.total_seconds() / 60:.1f} minutes")
                            
                            abandoned_users.add(user_dir_name)
                    except Exception as e:
                        log_print(f"Error checking user directory age for {user_dir_name}: {str(e)}")
            except Exception as e:
                log_print(f"Error checking for abandoned user directories: {str(e)}")
                
            for user_id in abandoned_users:
                user_dir = os.path.join(self.feedback_dir, user_id)
                if os.path.exists(user_dir):
                    try:
                        user_completion_count = self.get_user_completion_count(user_id)
                        if user_completion_count < self.max_scenarios_per_user:
                            log_print(f"User {user_id} has abandoned the study with {user_completion_count}/{self.max_scenarios_per_user} scenarios completed")
                            
                            self.cleanup_user_data(user_id)
                    except Exception as e:
                        log_print(f"Error during user directory cleanup for {user_id}: {str(e)}")
                        
            try:
                lock_files = glob.glob(os.path.join(self.lock_file_base, "*.lock"))
                for lock_file in lock_files:
                    try:
                        scenario_condition_key = os.path.basename(lock_file).replace(".lock", "")
                        if scenario_condition_key not in self.in_progress_scenarios:
                            try:
                                with open(lock_file, 'r') as f:
                                    content = f.read().strip()
                                log_print(f"Found orphaned lock file: {scenario_condition_key}, content: {content}")
                                
                                mtime = os.path.getmtime(lock_file)
                                file_age = datetime.now() - datetime.fromtimestamp(mtime)
                                if file_age > timeout_threshold:
                                    log_print(f"Removing orphaned lock file: {scenario_condition_key}, age: {file_age}")
                                    os.remove(lock_file)
                            except Exception as e:
                                log_print(f"Error processing orphaned lock file {scenario_condition_key}: {str(e)}")
                    except Exception as e:
                        log_print(f"Error checking lock file {os.path.basename(lock_file)}: {str(e)}")
            except Exception as e:
                log_print(f"Error scanning for orphaned lock files: {str(e)}")
    
    def _acquire_file_lock(self, scenario_condition_key, user_id):
        lock_file_path = os.path.join(self.lock_file_base, f"{scenario_condition_key}.lock")
        lock_file = None
        try:
            with open(lock_file_path, 'w') as f:
                f.write(f"{user_id}:{datetime.now().isoformat()}")
                f.flush()
                os.fsync(f.fileno())
            
            log_print(f"Created lock file: {lock_file_path} for user {user_id}")
            
            lock_file = open(lock_file_path, 'r+')
            
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            
            lock_file.seek(0)
            lock_file.truncate()
            lock_file.write(f"{user_id}:{datetime.now().isoformat()}")
            lock_file.flush()
            os.fsync(lock_file.fileno())
            
            return lock_file
        except IOError:
            if lock_file:
                lock_file.close()
            return False
        except Exception as e:
            log_print(f"Error acquiring lock for {scenario_condition_key}: {str(e)}")
            if lock_file:
                lock_file.close()
            return False
    
    def _release_file_lock(self, scenario_condition_key):
        lock_file_path = os.path.join(self.lock_file_base, f"{scenario_condition_key}.lock")
        try:
            if os.path.exists(lock_file_path):
                os.remove(lock_file_path)
                log_print(f"Released file lock for {scenario_condition_key}")
        except Exception as e:
            log_print(f"Error releasing lock for {scenario_condition_key}: {str(e)}")
    
    def mark_scenario_in_progress(self, user_id, scenario_id, condition):
        self.cleanup_abandoned_sessions()
        
        scenario_condition_key = f"{scenario_id}_{condition}"
        
        with self.state_lock:
            if scenario_condition_key in self.in_progress_scenarios:
                current_user = self.in_progress_scenarios[scenario_condition_key].get("user_id")
                if current_user != user_id:
                    log_print(f"Scenario {scenario_condition_key} already in progress by user {current_user}")
                    return False
                return True
            
            lock_handle = self._acquire_file_lock(scenario_condition_key, user_id)
            if not lock_handle:
                log_print(f"Could not acquire file lock for {scenario_condition_key} for user {user_id}")
                return False
                
            self.in_progress_scenarios[scenario_condition_key] = {
                "user_id": user_id,
                "timestamp": datetime.now(),
                "lock_handle": lock_handle
            }
            
            log_print(f"Marked scenario {scenario_condition_key} as in-progress for user {user_id}")
            return True
    
    def mark_scenario_completed(self, user_id, scenario_id, condition):
        """
        Mark a scenario as completed by a user.
        """
        scenario_condition_key = f"{scenario_id}_{condition}"
        
        with self.state_lock:
            if scenario_condition_key in self.in_progress_scenarios:
                lock_info = self.in_progress_scenarios[scenario_condition_key]
                if 'lock_handle' in lock_info:
                    try:
                        lock_info['lock_handle'].close()
                    except Exception as e:
                        log_print(f"Error closing lock file: {str(e)}")
                
                del self.in_progress_scenarios[scenario_condition_key]
                
                self._release_file_lock(scenario_condition_key)
                log_print(f"Released lock file for completed scenario: {scenario_condition_key}")
            
            if user_id not in self.user_completions:
                self.user_completions[user_id] = []
            
            if scenario_condition_key not in self.user_completions[user_id]:
                self.user_completions[user_id].append(scenario_condition_key)
            
            self.global_completions[scenario_condition_key] = self.global_completions.get(scenario_condition_key, 0) + 1
            
            log_print(f"Marked scenario {scenario_condition_key} as completed for user {user_id}")
            
            self._save_completion_to_disk(user_id, scenario_id, condition)
            
    def release_all_user_locks(self, user_id):
        log_print(f"Releasing locks for user {user_id}")
        
        with self.state_lock:
            user_locks = []
            for scenario_condition_key, info in self.in_progress_scenarios.items():
                if info.get("user_id") == user_id:
                    user_locks.append(scenario_condition_key)
            
            for key in user_locks:
                lock_info = self.in_progress_scenarios[key]
                if 'lock_handle' in lock_info:
                    try:
                        lock_info['lock_handle'].close()
                    except Exception as e:
                        log_print(f"Error closing lock file for {key}: {str(e)}")
                
                del self.in_progress_scenarios[key]
                self._release_file_lock(key)
            
            if user_locks:
                log_print(f"Released {len(user_locks)} locks for user {user_id}")
            
            try:
                all_lock_files = glob.glob(os.path.join(self.lock_file_base, "*.lock"))
                for lock_file in all_lock_files:
                    try:
                        with open(lock_file, 'r') as f:
                            lock_content = f.read().strip()
                        
                        if user_id in lock_content:
                            os.remove(lock_file)
                    except Exception:
                        pass
            except Exception as e:
                log_print(f"Error checking for orphaned lock files: {str(e)}")
    
    def _save_completion_to_disk(self, user_id, scenario_id, condition):
        try:
            user_dir = os.path.join(self.feedback_dir, user_id)
            os.makedirs(user_dir, exist_ok=True)
            
            completion_data = {
                "timestamp": datetime.now().isoformat(),
                "scenario_id": scenario_id,
                "condition": condition,
                "status": "completed"
            }
            
            completion_file = os.path.join(user_dir, f"completion_{scenario_id}_{condition}.json")
            with open(completion_file, 'w') as f:
                json.dump(completion_data, f, indent=2)
                
            log_print(f"Saved completion record to {completion_file}")
        except Exception as e:
            log_print(f"Error saving completion record: {str(e)}")
    
    def get_user_completion_count(self, user_id):
        with self.state_lock:
            if user_id not in self.user_completions:
                return 0
            return len(self.user_completions[user_id])
    
    def has_user_completed_all_scenarios(self, user_id):
        return self.get_user_completion_count(user_id) >= self.max_scenarios_per_user
    
    def get_user_completed_scenarios(self, user_id):
        with self.state_lock:
            if user_id not in self.user_completions:
                return []
            
            completed_scenarios = set()
            for scenario_condition in self.user_completions[user_id]:
                scenario_id, _ = scenario_condition.split('_', 1)
                completed_scenarios.add(scenario_id)
            
            return list(completed_scenarios)
    
    def select_next_scenario_for_user(self, user_id):
        # Run cleanup of abandoned sessions
        self.cleanup_abandoned_sessions()
        
        with self.state_lock:
            if self.has_user_completed_all_scenarios(user_id):
                log_print(f"User {user_id} has completed all scenarios")
                return None, None
            
            all_scenarios = self.get_available_scenarios()
            if not all_scenarios:
                log_print("No scenarios available")
                return None, None
            
            completed_scenarios = self.get_user_completed_scenarios(user_id)
            available_scenarios = [s for s in all_scenarios if s not in completed_scenarios]
            
            log_print(f"USER SELECTION - User {user_id}: completed {len(completed_scenarios)}/{len(all_scenarios)} scenarios")
            log_print(f"USER SELECTION - Completed scenarios: {completed_scenarios}")
            log_print(f"USER SELECTION - Available scenarios: {available_scenarios}")
            
            if not available_scenarios:
                log_print(f"User {user_id} has no new scenarios to complete")
                return None, None
            
            user_experienced_conditions = set()
            if user_id in self.user_completions:
                for scenario_condition in self.user_completions[user_id]:
                    _, condition = scenario_condition.split('_', 1)
                    user_experienced_conditions.add(condition)
                    
            log_print(f"USER SELECTION - Conditions already experienced: {user_experienced_conditions}")
            
            random.shuffle(available_scenarios)
            
            max_attempts = 3
            attempt = 0
            
            while attempt < max_attempts:
                attempt += 1
                
                for selected_scenario in available_scenarios:
                    all_conditions = self.get_available_conditions(selected_scenario)
                    if not all_conditions:
                        log_print(f"No conditions available for scenario {selected_scenario}")
                        continue
                        
                    unused_conditions = [c for c in all_conditions if c not in user_experienced_conditions]
                    
                    log_print(f"USER SELECTION - For scenario {selected_scenario}, unused conditions: {unused_conditions}")
                    
                    if unused_conditions:
                        condition_counts = {}
                        for condition in unused_conditions:
                            scenario_condition_key = f"{selected_scenario}_{condition}"
                            condition_counts[condition] = self.global_completions.get(scenario_condition_key, 0)
                        
                        sorted_conditions = sorted(condition_counts.items(), key=lambda x: x[1])
                        
                        min_count = sorted_conditions[0][1]
                        least_completed = [c for c, count in sorted_conditions if count == min_count]
                        
                        log_print(f"USER SELECTION - Condition counts: {condition_counts}")
                        log_print(f"USER SELECTION - Least completed unused conditions: {least_completed} (count: {min_count})")
                        
                        selected_condition = random.choice(least_completed)
                    else:
                        condition_counts = {}
                        for condition in all_conditions:
                            scenario_condition_key = f"{selected_scenario}_{condition}"
                            condition_counts[condition] = self.global_completions.get(scenario_condition_key, 0)
                        
                        sorted_conditions = sorted(condition_counts.items(), key=lambda x: x[1])
                        
                        min_count = sorted_conditions[0][1]
                        least_completed = [c for c, count in sorted_conditions if count == min_count]
                        
                        selected_condition = random.choice(least_completed)
                    
                    success = self.mark_scenario_in_progress(user_id, selected_scenario, selected_condition)
                    
                    if success:
                        log_print(f"USER SELECTION - SELECTED: scenario {selected_scenario} with condition {selected_condition} for user {user_id}")
                        return selected_scenario, selected_condition
                    else:
                        log_print(f"USER SELECTION - Could not mark scenario {selected_scenario} with condition {selected_condition} as in-progress, retrying")
                
                if attempt < max_attempts:
                    log_print(f"Could not find an available scenario-condition pair on attempt {attempt}, retrying in 0.5 seconds")
                    time.sleep(0.5)
            
            log_print(f"Could not find a valid scenario-condition pair for user {user_id} after {max_attempts} attempts")
            return None, None
    
    def cleanup_user_data(self, user_id):
        if not user_id:
            log_print("Cannot cleanup user data: No user ID provided")
            return False
            
        log_print(f"Performing complete cleanup for user {user_id}")
        
        with self.state_lock:
            try:
                self.release_all_user_locks(user_id)
                
                completed_scenario_conditions = []
                if user_id in self.user_completions:
                    completed_scenario_conditions = self.user_completions[user_id].copy()
                    completion_count = len(completed_scenario_conditions)
                    log_print(f"User {user_id} has {completion_count} completed scenarios")
                else:
                    log_print(f"User {user_id} has no completion records in memory")
                
                user_dir = os.path.join(self.feedback_dir, user_id)
                if os.path.exists(user_dir) and os.path.isdir(user_dir):
                    file_count = len([f for f in os.listdir(user_dir) if os.path.isfile(os.path.join(user_dir, f))])
                    log_print(f"Backing up user directory: {user_id} with {file_count} files")
                    
                    backup_dir = os.path.join(self.feedback_dir, "abandoned")
                    os.makedirs(backup_dir, exist_ok=True)
                    
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    user_backup_dir = os.path.join(backup_dir, f"{user_id}_{timestamp}")
                    
                    import shutil
                    try:
                        shutil.move(user_dir, user_backup_dir)
                        log_print(f"Moved user data to backup: {user_backup_dir}")
                    except Exception as e:
                        log_print(f"Error backing up user directory: {str(e)}")
                else:
                    log_print(f"No feedback directory found for user {user_id}")
                
                if user_id in self.user_completions:
                    del self.user_completions[user_id]
                    log_print(f"Removed user {user_id} from completion tracking")
                    
                    for scenario_condition_key in completed_scenario_conditions:
                        if scenario_condition_key in self.global_completions:
                            self.global_completions[scenario_condition_key] -= 1
                            if self.global_completions[scenario_condition_key] <= 0:
                                del self.global_completions[scenario_condition_key]
                                log_print(f"Removed {scenario_condition_key} from global completions")
                            else:
                                log_print(f"Decremented completion count for {scenario_condition_key} to {self.global_completions[scenario_condition_key]}")
                    
                    if completed_scenario_conditions:
                        log_print(f"Released {len(completed_scenario_conditions)} scenario-conditions back to the available pool")
                
                return True
                
            except Exception as e:
                log_print(f"Error during user cleanup for {user_id}: {str(e)}")
                return False

    def find_locked_scenario_for_user(self, user_id):
        if not user_id:
            log_print("Cannot find locked scenarios: No user ID provided")
            return None, None
        
        log_print(f"Checking for locked scenarios for user {user_id}")
        
        with self.state_lock:
            for scenario_condition_key, info in self.in_progress_scenarios.items():
                current_user = info.get("user_id")
                if current_user == user_id:
                    scenario_id, condition = scenario_condition_key.split('_', 1)
                    log_print(f"Found in-memory locked scenario for user {user_id}: {scenario_id}, condition: {condition}")
                    return scenario_id, condition
        
        try:
            lock_files = glob.glob(os.path.join(self.lock_file_base, "*.lock"))
            for lock_file in lock_files:
                try:
                    with open(lock_file, 'r') as f:
                        content = f.read().strip()
                    
                    if content.startswith(f"{user_id}:"):
                        scenario_condition_key = os.path.basename(lock_file).replace(".lock", "")
                        scenario_id, condition = scenario_condition_key.split('_', 1)
                        
                        log_print(f"Found existing lock file for user {user_id}: {scenario_id}, condition: {condition}")
                        
                        success = self.mark_scenario_in_progress(user_id, scenario_id, condition)
                        if success:
                            log_print(f"Successfully reacquired lock for scenario {scenario_id}, condition: {condition}")
                            return scenario_id, condition
                        else:
                            log_print(f"Failed to reacquire lock for scenario {scenario_id}, condition: {condition}")
                except Exception as e:
                    log_print(f"Error checking lock file {os.path.basename(lock_file)}: {str(e)}")
        except Exception as e:
            log_print(f"Error scanning for locked scenarios: {str(e)}")
        
        log_print(f"No locked scenarios found for user {user_id}")
        return None, None

task_distributor = None 