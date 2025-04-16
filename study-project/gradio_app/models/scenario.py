# Handles scenario management and loading for the chat application
import os
import json
import random

import gradio as gr
from gradio_app.config import settings
from gradio_app.utils.logger import log_print
from gradio_app.models.selection_algorithm import TaskDistributor

class ScenarioManager:
    """
    Manages scenarios for the study, including loading, tracking, and transitioning
    between different scenarios and conditions.
    """
    
    def __init__(self):
        self.scenarios_dir = os.path.abspath(os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
            "answers"
        ))
        
        self.feedback_dir = os.path.abspath(os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
            "feedback"
        ))
        
        self.available_scenarios = []
        
        from gradio_app.models.selection_algorithm import task_distributor
        import sys
        sys.modules['gradio_app.models.selection_algorithm'].task_distributor = TaskDistributor(
            self.scenarios_dir, self.feedback_dir
        )
        self.task_distributor = sys.modules['gradio_app.models.selection_algorithm'].task_distributor
        
        self.available_scenarios = self._discover_available_scenarios()
        log_print(f"ScenarioManager initialized with {len(self.available_scenarios)} scenarios")
    
    #-------------------------------------------------------------------------
    # SCENARIO DISCOVERY METHODS
    #-------------------------------------------------------------------------
    
    def _discover_available_scenarios(self):
        if not os.path.exists(self.scenarios_dir):
            log_print(f"Scenarios directory not found: {self.scenarios_dir}")
            return []
            
        available_scenarios = [
            folder for folder in os.listdir(self.scenarios_dir) 
            if os.path.isdir(os.path.join(self.scenarios_dir, folder))
        ]
        log_print(f"Found {len(available_scenarios)} scenario directories")
        return available_scenarios
    
    def _get_conditions_for_scenario(self, scenario_id):
        scenario_path = os.path.join(self.scenarios_dir, scenario_id)
        if not os.path.exists(scenario_path):
            log_print(f"Scenario directory not found: {scenario_path}")
            return []
            
        conditions = [
            folder for folder in os.listdir(scenario_path) 
            if os.path.isdir(os.path.join(scenario_path, folder))
        ]
        
        if not conditions:
            log_print(f"No condition folders found for scenario {scenario_id}")
            return []
            
        return conditions
    
    #-------------------------------------------------------------------------
    # SCENARIO DATA METHODS
    #-------------------------------------------------------------------------
    
    def _create_default_scenario(self):
        log_print("Creating default scenario as no scenarios were found")
        return {
            "title": "Error",
            "description": "Error - no scenario data found.",
            "task": "Error - no scenario data found.",
            "header": "Error - no scenario data found.",
            "welcome_message": "Error - no scenario data found.",
            "condition": {"latency": "fast", "complexity": "easy"}
        }
    
    def _validate_scenario_data(self, scenario_data, scenario_id, condition):
        required_fields = ["title", "description", "task", "welcome_message", "condition", "question"]
        missing_fields = [field for field in required_fields if field not in scenario_data]
        
        if missing_fields:
            log_print(f"Error: Missing required fields {missing_fields} in scenario {scenario_id}, condition {condition}")
            gr.Warning(f"Scenario {scenario_id} is missing required fields: {', '.join(missing_fields)}")
            return False
        
        if len(scenario_data) > len(required_fields):
            log_print(f"Error: Too many fields present in scenario {scenario_id}, condition {condition}")
            gr.Warning(f"Scenario {scenario_id} has too many fields: {len(scenario_data)}")
            return False
        return True
        
    def _load_scenario_data(self, scenario_id, condition):
        scenario_path = os.path.join(self.scenarios_dir, scenario_id, condition, "scenario.json")
        if not os.path.exists(scenario_path):
            log_print(f"Scenario file not found: {scenario_path}")
            gr.Warning(f"Scenario file not found for {scenario_id}/{condition}")
            return None
            
        try:
            with open(scenario_path, "r", encoding="utf-8") as f:
                scenario_data = json.load(f)
                
            if not self._validate_scenario_data(scenario_data, scenario_id, condition):
                gr.Warning(f"Invalid scenario data for {scenario_id}/{condition}")
                return None
                
            return scenario_data
        except Exception as e:
            log_print(f"Error loading scenario data: {str(e)}")
            gr.Warning(f"Error loading scenario: {str(e)}")
            return None

scenario_manager = ScenarioManager() 