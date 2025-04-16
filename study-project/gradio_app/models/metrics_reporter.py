import os
import json
import requests
import logging
from datetime import datetime
from collections import Counter, defaultdict
import glob

from gradio_app.utils.logger import log_print
from gradio_app.models.scenario import scenario_manager
from gradio_app.models.metrics_visualizer import metrics_visualizer
from gradio_app.config import settings

class MetricsReporter:
    def __init__(self, recipient_email=None):
        self.recipient_email = recipient_email or os.getenv("RECIPIENT_EMAIL", "Samuel.Bullard@stud.uni-regensburg.de")
        self.mailgun_api_key = os.getenv("MAILGUN_API_KEY", "")
        self.mailgun_domain = os.getenv("MAILGUN_DOMAIN", "")
        
        log_print("MetricsReporter initialized")
    
    def generate_report(self):
        # Get task_distributor from scenario_manager
        task_distributor = getattr(scenario_manager, 'task_distributor', None)
        
        if not task_distributor:
            log_print("Task distributor not initialized, cannot generate report")
            return {"error": "Task distributor not initialized"}
        
        # Get current timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Basic user stats
        total_users = len(task_distributor.user_completions)
        active_users = self._count_active_users(task_distributor)
        
        # Completion stats
        completion_counts = self._get_completion_counts(task_distributor)
        users_completed_all = self._count_users_completed_all(task_distributor)
        
        # Scenario distribution stats
        scenario_distribution = self._get_scenario_distribution(task_distributor)
        condition_distribution = self._get_condition_distribution(task_distributor)
        
        # In-progress stats
        in_progress_count = len(task_distributor.in_progress_scenarios)
        lock_file_count = self._count_lock_files(task_distributor)
        
        # Feedback rating stats
        feedback_stats = self._get_feedback_rating_stats(task_distributor.feedback_dir)
        
        # Compile the report
        report = {
            "timestamp": timestamp,
            "user_stats": {
                "total_users": total_users,
                "active_users": active_users,
                "users_completed_all": users_completed_all
            },
            "completion_stats": {
                "total_completions": sum(completion_counts.values()),
                "completion_counts": completion_counts,
                "average_completions_per_user": self._calculate_average_completions(task_distributor)
            },
            "distribution_stats": {
                "scenario_distribution": scenario_distribution,
                "condition_distribution": condition_distribution
            },
            "feedback_stats": feedback_stats,
            "current_state": {
                "in_progress_scenarios": in_progress_count,
                "lock_files": lock_file_count
            }
        }
        
        log_print(f"Generated metrics report at {timestamp}")
        return report
    
    def _count_active_users(self, task_distributor):
        return sum(1 for user, completions in task_distributor.user_completions.items() 
                  if len(completions) > 0)
    
    def _get_completion_counts(self, task_distributor):
        counts = Counter()
        for user, completions in task_distributor.user_completions.items():
            unique_scenarios = set()
            for completion in completions:
                scenario_id = completion.split('_')[0]
                unique_scenarios.add(scenario_id)
            counts[len(unique_scenarios)] += 1
        
        for i in range(5):
            if i not in counts:
                counts[i] = 0
                
        return dict(sorted(counts.items()))
    
    def _count_users_completed_all(self, task_distributor):
        return sum(1 for user, completions in task_distributor.user_completions.items() 
                  if task_distributor.has_user_completed_all_scenarios(user))
    
    def _get_scenario_distribution(self, task_distributor):
        scenario_counts = Counter()
        for user, completions in task_distributor.user_completions.items():
            for completion in completions:
                scenario_id = completion.split('_')[0]
                scenario_counts[scenario_id] += 1
        
        return dict(sorted(scenario_counts.items()))
    
    def _get_condition_distribution(self, task_distributor):
        condition_counts = Counter()
        for scenario_condition, count in task_distributor.global_completions.items():
            _, condition = scenario_condition.split('_', 1)
            condition_counts[condition] += count
        
        return dict(sorted(condition_counts.items()))
    
    def _calculate_average_completions(self, task_distributor):
        if not task_distributor.user_completions:
            return 0
            
        total_completions = sum(len(completions) for completions in task_distributor.user_completions.values())
        return round(total_completions / len(task_distributor.user_completions), 2)
    
    def _get_feedback_rating_stats(self, feedback_dir):
        if not os.path.exists(feedback_dir):
            return {"error": "Feedback directory not found"}
        
        # Track ratings by category and scenario
        ratings_by_category = defaultdict(list)
        ratings_by_scenario = defaultdict(lambda: defaultdict(list))
        ratings_by_condition = defaultdict(lambda: defaultdict(list))
        
        # Count total feedback files
        feedback_file_count = 0
        
        # Scan user directories
        for user_id in os.listdir(feedback_dir):
            user_dir = os.path.join(feedback_dir, user_id)
            if not os.path.isdir(user_dir) or user_id == "locks":
                continue
                
            feedback_files = glob.glob(os.path.join(user_dir, "feedback_*.json"))
            feedback_file_count += len(feedback_files)
            
            for feedback_path in feedback_files:
                try:
                    with open(feedback_path, 'r', encoding='utf-8') as f:
                        feedback_data = json.load(f)
                    
                    scenario_id = feedback_data.get('scenario_id')
                    condition = feedback_data.get('condition')
                    ratings = feedback_data.get('ratings', {})
                    
                    for category, rating in ratings.items():
                        ratings_by_category[category].append(rating)
                        if scenario_id:
                            ratings_by_scenario[scenario_id][category].append(rating)
                        if condition:
                            ratings_by_condition[condition][category].append(rating)
                            
                except Exception as e:
                    log_print(f"Error reading feedback file {feedback_path}: {str(e)}")
        
        category_stats = {}
        for category, ratings in ratings_by_category.items():
            if ratings:
                category_stats[category] = {
                    "avg": round(sum(ratings) / len(ratings), 2),
                    "count": len(ratings),
                    "min": min(ratings),
                    "max": max(ratings)
                }
        
        scenario_stats = {}
        for scenario_id, categories in ratings_by_scenario.items():
            scenario_stats[scenario_id] = {}
            for category, ratings in categories.items():
                if ratings:
                    scenario_stats[scenario_id][category] = round(sum(ratings) / len(ratings), 2)
        
        condition_stats = {}
        for condition, categories in ratings_by_condition.items():
            condition_stats[condition] = {}
            for category, ratings in categories.items():
                if ratings:
                    condition_stats[condition][category] = round(sum(ratings) / len(ratings), 2)
        
        return {
            "total_feedback_files": feedback_file_count,
            "category_stats": category_stats,
            "scenario_stats": scenario_stats,
            "condition_stats": condition_stats
        }
    
    def _count_lock_files(self, task_distributor):
        lock_file_base = task_distributor.lock_file_base
        if not os.path.exists(lock_file_base):
            return 0
        
        lock_files = glob.glob(os.path.join(lock_file_base, "*.lock"))
        return len(lock_files)
    
    def format_email_body(self, report, image_urls=None):
        if "error" in report:
            return f"Error generating report: {report['error']}"
        
        has_images = image_urls and len(image_urls) > 0
        
        # Start HTML email body
        body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Study Progress Report - {report['timestamp']}</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; }}
                h1, h2, h3 {{ color: #2c5282; }}
                h1 {{ border-bottom: 2px solid #4299e1; padding-bottom: 10px; }}
                h2 {{ border-bottom: 1px solid #4299e1; padding-bottom: 5px; margin-top: 30px; }}
                h3 {{ margin-top: 20px; }}
                .stat-item {{ margin-bottom: 5px; }}
                .stat-value {{ font-weight: bold; }}
                .chart-container {{ margin: 20px 0; text-align: center; }}
                .chart-container img {{ max-width: 100%; height: auto; border: 1px solid #e2e8f0; border-radius: 5px; }}
                table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
                th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background-color: #f1f5f9; }}
                .footer {{ margin-top: 40px; font-size: 12px; color: #718096; text-align: center; }}
                .study-info {{ background-color: #edf2f7; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
                .study-info h3 {{ margin-top: 0; }}
                .highlight {{ background-color: #fffde7; padding: 10px; border-left: 4px solid #ffc107; }}
            </style>
        </head>
        <body>
            <h1>Study Progress Report - {report['timestamp']}</h1>
            
            <div class="study-info">
                <h3>AI Interaction Study Overview</h3>
                <p>Study design: 2×2 factorial within-subjects design examining how trust in AI-generated health advice varies based on:</p>
                <ul>
                    <li><strong>Response Latency:</strong> Fast vs. Slow</li>
                    <li><strong>Cognitive Complexity:</strong> Easy vs. Hard</li>
                </ul>
                <p>Each participant completes all 4 conditions (one scenario per condition).</p>
            </div>
            
            <h2>User Statistics</h2>
            <div class="stat-item">Total Users: <span class="stat-value">{report['user_stats']['total_users']}</span></div>
            <div class="stat-item">Active Users (at least one completion): <span class="stat-value">{report['user_stats']['active_users']}</span></div>
            <div class="stat-item">Users Completed All Scenarios: <span class="stat-value">{report['user_stats']['users_completed_all']}</span></div>
        """
        
        # Add completion statistics section
        body += f"""
            <h2>Completion Statistics</h2>
            <div class="stat-item">Total Scenario Completions: <span class="stat-value">{report['completion_stats']['total_completions']}</span></div>
            <div class="stat-item">Average Completions Per User: <span class="stat-value">{report['completion_stats']['average_completions_per_user']}</span></div>
            
            <h3>Completion Breakdown</h3>
            <table>
                <tr>
                    <th>Scenarios Completed</th>
                    <th>Number of Users</th>
                </tr>
        """
        
        # Add completion breakdown table rows
        for count, users in report['completion_stats']['completion_counts'].items():
            body += f"""
                <tr>
                    <td>{count}</td>
                    <td>{users}</td>
                </tr>
            """
        
        body += """
            </table>
        """
        
        # Add completion chart
        if has_images and "completion_chart" in image_urls:
            body += f"""
            <div class="chart-container">
                <img src="{image_urls['completion_chart']}" alt="User Completion Distribution Chart">
            </div>
            """
        
        # Add scenario distribution section
        body += """
            <h2>Scenario Distribution</h2>
            <table>
                <tr>
                    <th>Scenario ID</th>
                    <th>Completions</th>
                </tr>
        """
        
        # Add scenario distribution table rows
        for scenario, count in report['distribution_stats']['scenario_distribution'].items():
            body += f"""
                <tr>
                    <td>{scenario}</td>
                    <td>{count}</td>
                </tr>
            """
        
        body += """
            </table>
        """
        
        # Add scenario chart
        if has_images and "scenario_chart" in image_urls:
            body += f"""
            <div class="chart-container">
                <img src="{image_urls['scenario_chart']}" alt="Scenario Distribution Chart">
            </div>
            """
        
        # Add experimental design section
        body += """
            <h2>Experimental Condition Distribution</h2>
            <p>This 2×2 factorial design examines how response latency (Fast/Slow) and cognitive complexity (Easy/Hard) affect trust in AI health advice.</p>
        """
        
        # Add 2×2 design chart if available
        if has_images and "design_chart" in image_urls:
            body += f"""
            <div class="chart-container">
                <img src="{image_urls['design_chart']}" alt="2×2 Factorial Design Distribution Chart">
                <p><em>Completion counts for each experimental condition in the 2×2 design.</em></p>
            </div>
            """
        
        # Add condition distribution section
        body += """
            <h3>Condition Details</h3>
            <table>
                <tr>
                    <th>Condition</th>
                    <th>Completions</th>
                </tr>
        """
        
        # Add condition distribution table rows
        for condition, count in report['distribution_stats']['condition_distribution'].items():
            body += f"""
                <tr>
                    <td>{condition}</td>
                    <td>{count}</td>
                </tr>
            """
        
        body += """
            </table>
        """
        
        # Add condition chart
        if has_images and "condition_chart" in image_urls:
            body += f"""
            <div class="chart-container">
                <img src="{image_urls['condition_chart']}" alt="Condition Distribution Chart">
            </div>
            """
        
        # Add feedback statistics section
        if "feedback_stats" in report and "category_stats" in report["feedback_stats"]:
            body += f"""
            <h2>Feedback Ratings</h2>
            <div class="stat-item">Total Feedback Files: <span class="stat-value">{report['feedback_stats']['total_feedback_files']}</span></div>
            
            <h3>Average Ratings by Category</h3>
            <p>Ratings are on a 7-point Likert scale (1-7) where 4 is neutral.</p>
            <table>
                <tr>
                    <th>Category</th>
                    <th>Average</th>
                    <th>Min</th>
                    <th>Max</th>
                    <th>Count</th>
                </tr>
            """
            
            for category, stats in report['feedback_stats']['category_stats'].items():
                css_class = "highlight" if "trust" in category.lower() else ""
                body += f"""
                <tr class="{css_class}">
                    <td>{category}</td>
                    <td>{stats['avg']}</td>
                    <td>{stats['min']}</td>
                    <td>{stats['max']}</td>
                    <td>{stats['count']}</td>
                </tr>
                """
            
            body += """
            </table>
            """
            
            # Add feedback ratings chart 
            if has_images and "feedback_chart" in image_urls:
                body += f"""
                <div class="chart-container">
                    <img src="{image_urls['feedback_chart']}" alt="Feedback Ratings Chart">
                </div>
                """
            
            # Add specialized trust visualization
            if has_images and "trust_chart" in image_urls:
                body += f"""
                <h3 class="highlight">Trust Analysis (Primary Research Question)</h3>
                <div class="chart-container">
                    <img src="{image_urls['trust_chart']}" alt="Trust Analysis Visualization">
                    <p><em>Visualization of trust ratings across the 2×2 experimental design conditions (Latency × Complexity).</em></p>
                </div>
                """
                
            # Add trust metrics comparison
            if has_images and "trust_metrics_chart" in image_urls:
                body += f"""
                <h3 class="highlight">Trust Metrics Comparison</h3>
                <div class="chart-container">
                    <img src="{image_urls['trust_metrics_chart']}" alt="Trust Metrics Comparison">
                    <p><em>Comparison of all trust-related metrics across experimental conditions, showing latency and complexity effects.</em></p>
                </div>
                <div class="study-info">
                    <p><strong>Interpreting Trust Metrics:</strong></p>
                    <ul>
                        <li><strong>Latency Effect:</strong> The difference in trust ratings between fast and slow response conditions</li>
                        <li><strong>Complexity Effect:</strong> The difference in trust ratings between easy and hard complexity conditions</li>
                        <li><strong>Interaction Effect:</strong> How the combination of latency and complexity factors affects trust</li>
                    </ul>
                    <p><em>Note: The visualizations show estimated effect sizes based on mean differences. Formal statistical analysis (ANOVA) would be needed for significance testing.</em></p>
                </div>
                """
            
            # Add condition feedback chart
            if has_images and "condition_feedback_chart" in image_urls:
                body += f"""
                <h3>Feedback Ratings by Condition</h3>
                <div class="chart-container">
                    <img src="{image_urls['condition_feedback_chart']}" alt="Condition Feedback Comparison Chart">
                    <p><em>Comparison of all feedback ratings across experimental conditions.</em></p>
                </div>
                """
        
        # Add current state section
        body += f"""
            <h2>Current State</h2>
            <div class="stat-item">In-Progress Scenarios: <span class="stat-value">{report['current_state']['in_progress_scenarios']}</span></div>
            <div class="stat-item">Active Lock Files: <span class="stat-value">{report['current_state']['lock_files']}</span></div>
            
            <div class="footer">
                <p>This report was automatically generated on {report['timestamp']}.</p>
                <p>AI Interaction Study Metrics System</p>
            </div>
        </body>
        </html>
        """
        
        return body
    
    def format_text_email_body(self, report):
        if "error" in report:
            return f"Error generating report: {report['error']}"
            
        body = f"""
Study Progress Report - {report['timestamp']}
======================={('=' * len(report['timestamp']))}

USER STATISTICS
--------------
Total Users: {report['user_stats']['total_users']}
Active Users (at least one completion): {report['user_stats']['active_users']}
Users Completed All Scenarios: {report['user_stats']['users_completed_all']}

COMPLETION STATISTICS
-------------------
Total Scenario Completions: {report['completion_stats']['total_completions']}
Average Completions Per User: {report['completion_stats']['average_completions_per_user']}

Completion Breakdown:
"""
        # Add completion breakdown
        for count, users in report['completion_stats']['completion_counts'].items():
            body += f"  {count} scenarios completed: {users} users\n"
        
        # Add scenario distribution
        body += "\nSCENARIO DISTRIBUTION\n--------------------\n"
        for scenario, count in report['distribution_stats']['scenario_distribution'].items():
            body += f"  {scenario}: {count} completions\n"
        
        # Add condition distribution
        body += "\nCONDITION DISTRIBUTION\n---------------------\n"
        for condition, count in report['distribution_stats']['condition_distribution'].items():
            body += f"  {condition}: {count} completions\n"
        
        # Add feedback stats
        if "feedback_stats" in report and "category_stats" in report["feedback_stats"]:
            body += "\nFEEDBACK RATINGS\n---------------\n"
            body += f"Total Feedback Files: {report['feedback_stats']['total_feedback_files']}\n\n"
            
            body += "Average Ratings by Category:\n"
            for category, stats in report['feedback_stats']['category_stats'].items():
                body += f"  {category}: {stats['avg']} (min: {stats['min']}, max: {stats['max']}, count: {stats['count']})\n"
            
            body += "\nAverage Ratings by Scenario:\n"
            for scenario, categories in report['feedback_stats']['scenario_stats'].items():
                body += f"  {scenario}:\n"
                for category, avg in categories.items():
                    body += f"    {category}: {avg}\n"
            
            body += "\nAverage Ratings by Condition:\n"
            for condition, categories in report['feedback_stats']['condition_stats'].items():
                body += f"  {condition}:\n"
                for category, avg in categories.items():
                    body += f"    {category}: {avg}\n"
        
        body += f"\nCURRENT STATE\n------------\n"
        body += f"In-Progress Scenarios: {report['current_state']['in_progress_scenarios']}\n"
        body += f"Active Lock Files: {report['current_state']['lock_files']}\n"
        
        return body
    
    def send_email_report(self):
        if not self.mailgun_api_key:
            self.mailgun_api_key = os.getenv("MAILGUN_API_KEY", "")
        if not self.mailgun_domain:
            self.mailgun_domain = os.getenv("MAILGUN_DOMAIN", "")

        report = self.generate_report()
        
        image_urls = metrics_visualizer.create_visualizations(report)
        
        html_email = self.format_email_body(report, image_urls)
        text_email = self.format_text_email_body(report)
        email_subject = f"Study Progress Report - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        if not self.mailgun_api_key or not self.mailgun_domain:
            log_print("Mailgun credentials not configured. Cannot send email.")
            log_print("Report would have been sent to: " + self.recipient_email)
            log_print("Email subject: " + email_subject)
            log_print("Images generated: " + str(len(image_urls)))
            log_print("Email body preview: \n" + text_email[:500] + "...")
            return False
        
        try:
            response = requests.post(
                f"https://api.mailgun.net/v3/{self.mailgun_domain}/messages",
                auth=("api", self.mailgun_api_key),
                data={
                    "from": f"Study Metrics <mailgun@{self.mailgun_domain}>",
                    "to": [self.recipient_email],
                    "subject": email_subject,
                    "text": text_email,
                    "html": html_email
                }
            )
            
            if response.status_code == 200:
                log_print("Email report sent successfully with visualizations")
                return True
            else:
                log_print(f"Failed to send email report. Status code: {response.status_code}")
                log_print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            log_print(f"Error sending email report: {str(e)}")
            return False

metrics_reporter = MetricsReporter() 