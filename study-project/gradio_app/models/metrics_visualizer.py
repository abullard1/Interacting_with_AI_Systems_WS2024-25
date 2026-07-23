import os
import io
import base64
import requests
import logging
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
from datetime import datetime
from gradio_app.utils.logger import log_print
class MetricsVisualizer:
    
    def __init__(self, imgbb_api_key=None):
        self.imgbb_api_key = imgbb_api_key or os.getenv("IMGBB_API_KEY", "")
        
        plt.style.use('seaborn-v0_8-darkgrid')
        
        self.cache_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                                     "logs", "metrics_images")
        os.makedirs(self.cache_dir, exist_ok=True)
        
        self.condition_colors = {
            'fast_easy': '#4a86e8',  # Blue
            'fast_hard': '#6aa84f',  # Green
            'slow_easy': '#e69138',  # Orange
            'slow_hard': '#cc0000',  # Red
            'unknown': '#999999'     # Grey (fallback)
        }
        
        self.condition_labels = {
            'fast_easy': 'Fast + Easy',
            'fast_hard': 'Fast + Hard',
            'slow_easy': 'Slow + Easy',
            'slow_hard': 'Slow + Hard'
        }
        
        log_print("MetricsVisualizer initialized")
    
    def create_visualizations(self, report_data):
        if "error" in report_data:
            log_print(f"Error in report data: {report_data['error']}")
            return {}
            
        deleted_count = self.cleanup_old_cache_files(max_age_days=7)  # Keep files for 7 days
        if deleted_count > 0:
            log_print(f"Cleaned up {deleted_count} old cache files")
        
        image_urls = {}
        
        try:
            completion_counts = report_data["completion_stats"]["completion_counts"]
            completion_chart_path = self._create_completion_chart(completion_counts, "standard")
            if completion_chart_path:
                completion_url = self._upload_image(completion_chart_path, "completion_distribution")
                if completion_url:
                    image_urls["completion_chart"] = completion_url
            
            scenario_dist = report_data["distribution_stats"]["scenario_distribution"]
            scenario_chart_path = self._create_scenario_distribution_chart(scenario_dist, "standard")
            if scenario_chart_path:
                scenario_url = self._upload_image(scenario_chart_path, "scenario_distribution")
                if scenario_url:
                    image_urls["scenario_chart"] = scenario_url
            
            condition_dist = report_data["distribution_stats"]["condition_distribution"]
            condition_chart_path = self._create_condition_distribution_chart(condition_dist, "standard")
            if condition_chart_path:
                condition_url = self._upload_image(condition_chart_path, "condition_distribution")
                if condition_url:
                    image_urls["condition_chart"] = condition_url
            
            design_chart_path = self._create_2x2_design_chart(condition_dist, "standard")
            if design_chart_path:
                design_url = self._upload_image(design_chart_path, "design_distribution") 
                if design_url:
                    image_urls["design_chart"] = design_url
            
            if "feedback_stats" in report_data and "category_stats" in report_data["feedback_stats"]:
                feedback_stats = report_data["feedback_stats"]["category_stats"]
                feedback_chart_path = self._create_feedback_ratings_chart(feedback_stats, "standard")
                if feedback_chart_path:
                    feedback_url = self._upload_image(feedback_chart_path, "feedback_ratings")
                    if feedback_url:
                        image_urls["feedback_chart"] = feedback_url
                
                if "condition_stats" in report_data["feedback_stats"]:
                    condition_feedback = report_data["feedback_stats"]["condition_stats"]
                    
                    cond_feedback_path = self._create_condition_feedback_chart(condition_feedback, "standard")
                    if cond_feedback_path:
                        cond_feedback_url = self._upload_image(cond_feedback_path, "condition_feedback")
                        if cond_feedback_url:
                            image_urls["condition_feedback_chart"] = cond_feedback_url
                    
                    trust_chart_path = self._create_trust_visualization(condition_feedback, "standard")
                    if trust_chart_path:
                        trust_url = self._upload_image(trust_chart_path, "trust_visualization")
                        if trust_url:
                            image_urls["trust_chart"] = trust_url
                            
                    trust_metrics_path = self._create_trust_metrics_comparison(condition_feedback, "standard")
                    if trust_metrics_path:
                        trust_metrics_url = self._upload_image(trust_metrics_path, "trust_metrics_comparison")
                        if trust_metrics_url:
                            image_urls["trust_metrics_chart"] = trust_metrics_url
            
            log_print(f"Created {len(image_urls)} visualization charts")
            return image_urls
            
        except Exception as e:
            log_print(f"Error creating visualizations: {str(e)}")
            return image_urls
    
    def _create_completion_chart(self, completion_counts, timestamp):
        fig, ax = plt.subplots(figsize=(10, 6))
        
        x = list(completion_counts.keys())
        y = list(completion_counts.values())
        
        bars = ax.bar(x, y, color='#4a86e8', width=0.6)
        
        for bar in bars:
            height = bar.get_height()
            ax.annotate(f'{height}',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha='center', va='bottom',
                        fontsize=12)
        
        ax.set_xlabel('Number of Scenarios Completed', fontsize=12)
        ax.set_ylabel('Number of Users', fontsize=12)
        ax.set_title('User Completion Distribution', fontsize=14, fontweight='bold')
        
        ax.annotate('Study design: Each user completes 4 scenarios (2×2 design)',
                   xy=(0.5, 0.95),
                   xycoords='axes fraction',
                   ha='center',
                   fontsize=10,
                   bbox=dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.7))
        
        ax.set_xticks(x)
        
        ax.grid(axis='y', linestyle='--', alpha=0.7)
        
        plt.tight_layout()
        
        output_path = os.path.join(self.cache_dir, f"completion_chart.png")
        plt.savefig(output_path, dpi=100, bbox_inches='tight')
        plt.close(fig)
        
        return output_path
    
    def _create_scenario_distribution_chart(self, scenario_dist, timestamp):
        fig, ax = plt.subplots(figsize=(10, 6))
        
        x = list(condition_dist.keys())
        y = list(condition_dist.values())
        
        colors = []
        formatted_labels = []
        
        for condition in x:
            if 'fast' in condition.lower() and 'easy' in condition.lower():
                condition_key = 'fast_easy'
            elif 'fast' in condition.lower() and 'hard' in condition.lower():
                condition_key = 'fast_hard'
            elif 'slow' in condition.lower() and 'easy' in condition.lower():
                condition_key = 'slow_easy'
            elif 'slow' in condition.lower() and 'hard' in condition.lower():
                condition_key = 'slow_hard'
            else:
                condition_key = 'unknown'
                
            colors.append(self.condition_colors[condition_key])
            formatted_labels.append(self.condition_labels.get(condition_key, condition))
        
        bars = ax.bar(x, y, color=colors, width=0.6)
        
        for bar in bars:
            height = bar.get_height()
            ax.annotate(f'{height}',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha='center', va='bottom',
                        fontsize=12)
        
        ax.set_xlabel('Condition', fontsize=12)
        ax.set_ylabel('Number of Completions', fontsize=12)
        ax.set_title('Condition Distribution', fontsize=14, fontweight='bold')
        
        ax.set_xticks(range(len(x)))
        ax.set_xticklabels(formatted_labels, rotation=45, ha='right')
        
        ax.annotate('Study design: 2×2 factorial design\nLatency (Fast/Slow) × Complexity (Easy/Hard)',
                   xy=(0.5, 0.95),
                   xycoords='axes fraction',
                   ha='center',
                   fontsize=10,
                   bbox=dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.7))
        
        ax.grid(axis='y', linestyle='--', alpha=0.7)
        
        plt.tight_layout()
        
        output_path = os.path.join(self.cache_dir, f"condition_chart.png")
        plt.savefig(output_path, dpi=100, bbox_inches='tight')
        plt.close(fig)
        
        return output_path
    
    def _create_2x2_design_chart(self, condition_dist, timestamp):
        fig, ax = plt.subplots(figsize=(12, 7))
        
        categories = list(feedback_stats.keys())
        averages = [stats["avg"] for stats in feedback_stats.values()]
        counts = [stats["count"] for stats in feedback_stats.values()]
        
        errors = [
            (stats["max"] - stats["min"]) / 4  # Rough approximation of standard deviation
            for stats in feedback_stats.values()
        ]
        
        colors = []
        for category in categories:
            if 'trust' in category.lower():
                colors.append('#ff9900')  # Highlight trust-related categories
            else:
                colors.append('#6fa8dc')
        
        bars = ax.barh(categories, averages, xerr=errors, color=colors, alpha=0.7, 
                   error_kw={'elinewidth': 2, 'capsize': 5})
        
        for i, bar in enumerate(bars):
            width = bar.get_width()
            ax.annotate(f'{width:.2f} (n={counts[i]})',
                        xy=(width, bar.get_y() + bar.get_height()/2),
                        xytext=(5, 0),
                        textcoords="offset points",
                        ha='left', va='center',
                        fontsize=10)
        
        ax.set_xlabel('Average Rating (Scale 1-7)', fontsize=12)
        ax.set_title('Average Feedback Ratings by Category', fontsize=14, fontweight='bold')
        
        ax.set_xlim(0.5, 7.5)
        ax.xaxis.set_major_locator(ticker.MultipleLocator(1))
        
        ax.axvline(x=4, color='gray', linestyle='--', alpha=0.7)
        
        trust_categories = [c for c in categories if 'trust' in c.lower()]
        if trust_categories:
            ax.annotate('Primary research question focuses on trust in AI',
                       xy=(0.5, 0.98),
                       xycoords='axes fraction',
                       ha='center',
                       fontsize=10,
                       bbox=dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.7))
        
        ax.grid(axis='x', linestyle='--', alpha=0.7)
        
        plt.tight_layout()
        
        output_path = os.path.join(self.cache_dir, f"feedback_chart.png")
        plt.savefig(output_path, dpi=100, bbox_inches='tight')
        plt.close(fig)
        
        return output_path
    
    def _create_condition_feedback_chart(self, condition_feedback, timestamp):
        if not condition_feedback or len(condition_feedback) == 0:
            log_print("No condition feedback data available for trust visualization")
            return None
            
        trust_category = None
        
        for condition, categories in condition_feedback.items():
            for category in categories.keys():
                if 'trust' in category.lower() or 'vertrauen' in category.lower():
                    trust_category = category
                    break
            if trust_category:
                break
                
        if not trust_category:
            log_print("No trust category found for specialized visualization")
            return None
        
        try:    
            fast_easy_trust = 0
            fast_hard_trust = 0
            slow_easy_trust = 0
            slow_hard_trust = 0
            
            has_fast_easy = False
            has_fast_hard = False
            has_slow_easy = False
            has_slow_hard = False
            
            for condition, categories in condition_feedback.items():
                condition_lower = condition.lower()
                if trust_category in categories:
                    if 'fast' in condition_lower and 'easy' in condition_lower:
                        fast_easy_trust = categories[trust_category]
                        has_fast_easy = True
                    elif 'fast' in condition_lower and 'hard' in condition_lower:
                        fast_hard_trust = categories[trust_category]
                        has_fast_hard = True
                    elif 'slow' in condition_lower and 'easy' in condition_lower:
                        slow_easy_trust = categories[trust_category]
                        has_slow_easy = True
                    elif 'slow' in condition_lower and 'hard' in condition_lower:
                        slow_hard_trust = categories[trust_category]
                        has_slow_hard = True
            
            condition_count = sum([has_fast_easy, has_fast_hard, has_slow_easy, has_slow_hard])
            if condition_count < 2:
                log_print(f"Insufficient condition data for trust visualization (only {condition_count} conditions with data)")
                return None
            
            fig = plt.figure(figsize=(15, 12))
            
            gs = plt.GridSpec(2, 2, height_ratios=[1, 1])
            
            ax1 = plt.subplot(gs[0, 0])
            
            data = np.array([[fast_easy_trust, fast_hard_trust], 
                            [slow_easy_trust, slow_hard_trust]])
            
            im = ax1.imshow(data, cmap='RdYlGn', vmin=1, vmax=7)
            
            ax1.set_xticks([0, 1])
            ax1.set_yticks([0, 1])
            ax1.set_xticklabels(['Low Cognitive Complexity', 'High Cognitive Complexity'], fontsize=10)
            ax1.set_yticklabels(['Low Latency', 'High Latency'], fontsize=10)
            
            ax1.set_xlabel('Cognitive Complexity Factor', fontsize=12)
            ax1.set_ylabel('Response Latency Factor', fontsize=12)
            
            ax1.set_title('Trust Ratings in 2×2 Factorial Design', fontsize=14, fontweight='bold')
            
            for i in range(2):
                for j in range(2):
                    text = ax1.text(j, i, f"{data[i, j]:.2f}",
                                ha="center", va="center", color="black",
                                fontsize=14, fontweight='bold')
            
            cbar = fig.colorbar(im, ax=ax1)
            cbar.set_label(f'{trust_category} (Scale 1-7)', fontsize=12)
            
            ax2 = plt.subplot(gs[0, 1])
            
            conditions = [
                'Low Latency\nLow Complexity', 
                'Low Latency\nHigh Complexity',
                'High Latency\nLow Complexity', 
                'High Latency\nHigh Complexity'
            ]
            
            trust_values = [fast_easy_trust, fast_hard_trust, slow_easy_trust, slow_hard_trust]
            colors = [self.condition_colors['fast_easy'], 
                    self.condition_colors['fast_hard'],
                    self.condition_colors['slow_easy'], 
                    self.condition_colors['slow_hard']]
            
            bars = ax2.bar(conditions, trust_values, color=colors, alpha=0.7)
            
            for bar in bars:
                height = bar.get_height()
                ax2.annotate(f'{height:.2f}',
                            xy=(bar.get_x() + bar.get_width() / 2, height),
                            xytext=(0, 3),
                            textcoords="offset points",
                            ha='center', va='bottom',
                            fontsize=12)
            
            ax2.set_xlabel('Experimental Condition', fontsize=12)
            ax2.set_ylabel(f'{trust_category} (Scale 1-7)', fontsize=12)
            ax2.set_title(f'Average Trust Ratings by Condition', fontsize=14, fontweight='bold')
            
            ax2.set_ylim(0, 7.5)
            ax2.yaxis.set_major_locator(ticker.MultipleLocator(1))
            
            ax2.axhline(y=4, color='gray', linestyle='--', alpha=0.7, label='Neutral Value')
            
            ax2.legend()
            
            plt.setp(ax2.get_xticklabels(), rotation=45, ha='right')
            
            ax3 = plt.subplot(gs[1, :])
            
            latency_effect = 0
            latency_effect_magnitude = 0
            
            if (has_fast_easy or has_fast_hard) and (has_slow_easy or has_slow_hard):
                fast_avg = 0
                slow_avg = 0
                fast_count = 0
                slow_count = 0
                
                if has_fast_easy:
                    fast_avg += fast_easy_trust
                    fast_count += 1
                if has_fast_hard:
                    fast_avg += fast_hard_trust
                    fast_count += 1
                if has_slow_easy:
                    slow_avg += slow_easy_trust
                    slow_count += 1
                if has_slow_hard:
                    slow_avg += slow_hard_trust
                    slow_count += 1
                
                if fast_count > 0:
                    fast_avg /= fast_count
                if slow_count > 0:
                    slow_avg /= slow_count
                
                latency_effect = slow_avg - fast_avg
                latency_effect_magnitude = abs(latency_effect)
            
            complexity_effect = 0
            complexity_effect_magnitude = 0
            
            if (has_fast_easy or has_slow_easy) and (has_fast_hard or has_slow_hard):
                easy_avg = 0
                hard_avg = 0
                easy_count = 0
                hard_count = 0
                
                if has_fast_easy:
                    easy_avg += fast_easy_trust
                    easy_count += 1
                if has_slow_easy:
                    easy_avg += slow_easy_trust
                    easy_count += 1
                if has_fast_hard:
                    hard_avg += fast_hard_trust
                    hard_count += 1
                if has_slow_hard:
                    hard_avg += slow_hard_trust
                    hard_count += 1
                
                if easy_count > 0:
                    easy_avg /= easy_count
                if hard_count > 0:
                    hard_avg /= hard_count
                
                complexity_effect = hard_avg - easy_avg
                complexity_effect_magnitude = abs(complexity_effect)
            
            interaction_effect = 0
            interaction_effect_magnitude = 0
            
            if has_fast_easy and has_fast_hard and has_slow_easy and has_slow_hard:
                fast_diff = fast_hard_trust - fast_easy_trust
                slow_diff = slow_hard_trust - slow_easy_trust
                interaction_effect = fast_diff - slow_diff
                interaction_effect_magnitude = abs(interaction_effect)
            
            comparison_labels = ['Latency Effect\n(High vs Low)', 
                                'Complexity Effect\n(High vs Low)', 
                                'Interaction Effect\n(Latency × Complexity)']
            
            comparison_values = [latency_effect, complexity_effect, interaction_effect]
            comparison_magnitudes = [latency_effect_magnitude, complexity_effect_magnitude, interaction_effect_magnitude]
            
            effect_colors = []
            for value in comparison_values:
                if value > 0:
                    effect_colors.append('#1a9850')  # Positive effect - green
                elif value < 0:
                    effect_colors.append('#d73027')  # Negative effect - red
                else:
                    effect_colors.append('#878787')  # No effect - gray
            
            bars = ax3.barh(comparison_labels, comparison_values, color=effect_colors, alpha=0.7)
            
            for i, bar in enumerate(bars):
                width = bar.get_width()
                alignment = 'left' if width < 0 else 'right'
                xpos = width - 0.1 if width < 0 else width + 0.1
                
                ax3.annotate(f'{width:.2f}',
                            xy=(width, bar.get_y() + bar.get_height()/2),
                            xytext=(5 * (-1 if width < 0 else 1), 0),
                            textcoords="offset points",
                            ha=alignment, va='center',
                            fontsize=12)
            
            ax3.axvline(x=0, color='black', linestyle='-', alpha=0.7)
            
            ax3.text(0.01, 0.05, 
                    "Interpretation:\n"
                    "- Positive Latency Effect: Higher trust with slower responses\n"
                    "- Positive Complexity Effect: Higher trust with complex responses\n"
                    "- Interaction Effect: How factors influence each other",
                    transform=ax3.transAxes, fontsize=10,
                    bbox=dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.9))
            
            ax3.set_title('Effect Sizes for Trust Ratings', fontsize=14, fontweight='bold')
            ax3.set_xlabel('Effect on Trust Rating (Scale Points)', fontsize=12)
            
            max_effect = max(comparison_magnitudes) if comparison_magnitudes else 0.5
            ax3.set_xlim(-max_effect-0.5, max_effect+0.5)
            
            ax3.grid(axis='x', linestyle='--', alpha=0.7)
            
            ax3.annotate('* Note: Visual representation of effects without formal significance testing. ' + 
                        'Interpretation requires statistical analysis.',
                    xy=(0.5, -0.15),
                    xycoords='axes fraction',
                    ha='center',
                    fontsize=10,
                    style='italic')
            
            fig.text(0.5, 0.01, 
                    'Primary Research Question: "How does perceived trust in AI-generated health-related advice\nvary as a function of (a) response latency (fast vs. slow) and (b) cognitive complexity (easy vs. hard)?"', 
                    ha='center', fontsize=11, weight='bold',
                    bbox=dict(boxstyle='round,pad=0.5', facecolor='#f0f0f0', alpha=0.9))
            
            fig.text(0.5, 0.97, 
                    f'Data collected on 7-point Likert scale. Category: "{trust_category}"', 
                    ha='center', fontsize=10, style='italic')
            
            plt.tight_layout(rect=[0, 0.05, 1, 0.95])
            
            output_path = os.path.join(self.cache_dir, f"trust_visualization.png")
            plt.savefig(output_path, dpi=100, bbox_inches='tight')
            plt.close(fig)
            
            return output_path
            
        except Exception as e:
            log_print(f"Error creating trust visualization: {str(e)}")
            return None
    
    def _create_trust_metrics_comparison(self, condition_feedback, timestamp):
        if not condition_feedback or len(condition_feedback) == 0:
            log_print("No condition feedback data available for trust metrics comparison")
            return None
        
        try:
            trust_categories = []
            
            for condition, categories in condition_feedback.items():
                for category in categories.keys():
                    if ('trust' in category.lower() or 'vertrauen' in category.lower()) and category not in trust_categories:
                        trust_categories.append(category)
            
            if not trust_categories:
                log_print("No trust-related categories found for comparison visualization")
                return None
            
            trust_categories.sort()
            
            conditions = {
                'fast_easy': None,
                'fast_hard': None,
                'slow_easy': None,
                'slow_hard': None
            }
            
            for condition in condition_feedback.keys():
                condition_lower = condition.lower()
                if 'fast' in condition_lower and 'easy' in condition_lower:
                    conditions['fast_easy'] = condition
                elif 'fast' in condition_lower and 'hard' in condition_lower:
                    conditions['fast_hard'] = condition
                elif 'slow' in condition_lower and 'easy' in condition_lower:
                    conditions['slow_easy'] = condition
                elif 'slow' in condition_lower and 'hard' in condition_lower:
                    conditions['slow_hard'] = condition
            
            condition_count = sum(1 for c in conditions.values() if c is not None)
            if condition_count < 2:
                log_print(f"Insufficient condition data for trust metrics comparison (only {condition_count} conditions)")
                return None
            
            
            num_rows = len(trust_categories) + 1  # +1 for the summary panel
            
            fig = plt.figure(figsize=(12, 4 * num_rows))
            gs = plt.GridSpec(num_rows, 2, height_ratios=[2] + [1] * (num_rows-1))
            
            ax_summary = plt.subplot(gs[0, :])
            
            ax_summary.text(0.5, 0.5, 
                "2×2 Factorial Design Analysis of Trust Metrics\n\n"
                "This visualization examines how various trust-related metrics vary across the experimental conditions:\n"
                "• Factor 1: Response Latency (Low/High)\n"
                "• Factor 2: Cognitive Complexity (Low/High)\n\n"
                "For each trust metric, two types of analysis are shown:\n"
                "1. Raw ratings across all four experimental conditions\n"
                "2. Main effects of each factor (calculated as mean differences)",
                ha='center', va='center', fontsize=12, transform=ax_summary.transAxes,
                bbox=dict(boxstyle='round,pad=1', facecolor='#f8f9fa', alpha=0.9))
            
            ax_summary.axis('off')
            
            for i, category in enumerate(trust_categories):
                row = i + 1  # +1 because row 0 is the summary panel
                
                ax_bars = plt.subplot(gs[row, 0])
                
                data = []
                labels = []
                colors = []
                
                condition_names = {
                    'fast_easy': 'Low Latency\nLow Complexity',
                    'fast_hard': 'Low Latency\nHigh Complexity',
                    'slow_easy': 'High Latency\nLow Complexity',
                    'slow_hard': 'High Latency\nHigh Complexity'
                }
                
                for key in ['fast_easy', 'fast_hard', 'slow_easy', 'slow_hard']:
                    if conditions[key] and conditions[key] in condition_feedback:
                        condition_data = condition_feedback[conditions[key]]
                        if category in condition_data:
                            data.append(condition_data[category])
                            labels.append(condition_names[key])
                            colors.append(self.condition_colors[key])
                
                bars = ax_bars.bar(labels, data, color=colors, alpha=0.7)
                
                for bar in bars:
                    height = bar.get_height()
                    ax_bars.annotate(f'{height:.2f}',
                                  xy=(bar.get_x() + bar.get_width() / 2, height),
                                  xytext=(0, 3),
                                  textcoords="offset points",
                                  ha='center', va='bottom',
                                  fontsize=9)
                
                ax_bars.set_title(f'{category}', fontsize=12, fontweight='bold')
                ax_bars.set_ylabel('Rating (1-7)', fontsize=10)
                
                ax_bars.set_ylim(0, 7.5)
                ax_bars.yaxis.set_major_locator(ticker.MultipleLocator(1))
                
                ax_bars.axhline(y=4, color='gray', linestyle='--', alpha=0.7, label='Neutral')
                
                ax_bars.grid(axis='y', linestyle='--', alpha=0.7)
                
                plt.setp(ax_bars.get_xticklabels(), rotation=45, ha='right', fontsize=8)
                
                ax_effects = plt.subplot(gs[row, 1])
                
                fast_condition_count = sum(1 for k in ['fast_easy', 'fast_hard'] if conditions[k] and conditions[k] in condition_feedback)
                slow_condition_count = sum(1 for k in ['slow_easy', 'slow_hard'] if conditions[k] and conditions[k] in condition_feedback)
                easy_condition_count = sum(1 for k in ['fast_easy', 'slow_easy'] if conditions[k] and conditions[k] in condition_feedback)
                hard_condition_count = sum(1 for k in ['fast_hard', 'slow_hard'] if conditions[k] and conditions[k] in condition_feedback)
                
                can_calculate_latency = fast_condition_count > 0 and slow_condition_count > 0
                can_calculate_complexity = easy_condition_count > 0 and hard_condition_count > 0
                
                can_calculate_interaction = all(conditions[k] and conditions[k] in condition_feedback for k in ['fast_easy', 'fast_hard', 'slow_easy', 'slow_hard'])
                
                if (can_calculate_latency or can_calculate_complexity):
                    has_category_data = True
                    
                    for k in ['fast_easy', 'fast_hard', 'slow_easy', 'slow_hard']:
                        if conditions[k] and conditions[k] in condition_feedback:
                            if category not in condition_feedback[conditions[k]]:
                                has_category_data = False
                                break
                    
                    if has_category_data:
                        latency_effect = 0
                        complexity_effect = 0
                        interaction_effect = 0
                        
                        if can_calculate_latency:
                            fast_vals = []
                            if conditions['fast_easy'] and conditions['fast_easy'] in condition_feedback and category in condition_feedback[conditions['fast_easy']]:
                                fast_vals.append(condition_feedback[conditions['fast_easy']][category])
                            if conditions['fast_hard'] and conditions['fast_hard'] in condition_feedback and category in condition_feedback[conditions['fast_hard']]:
                                fast_vals.append(condition_feedback[conditions['fast_hard']][category])
                            
                            slow_vals = []
                            if conditions['slow_easy'] and conditions['slow_easy'] in condition_feedback and category in condition_feedback[conditions['slow_easy']]:
                                slow_vals.append(condition_feedback[conditions['slow_easy']][category])
                            if conditions['slow_hard'] and conditions['slow_hard'] in condition_feedback and category in condition_feedback[conditions['slow_hard']]:
                                slow_vals.append(condition_feedback[conditions['slow_hard']][category])
                            
                            if fast_vals and slow_vals:
                                fast_avg = sum(fast_vals) / len(fast_vals)
                                slow_avg = sum(slow_vals) / len(slow_vals)
                                latency_effect = slow_avg - fast_avg
                        
                        if can_calculate_complexity:
                            easy_vals = []
                            if conditions['fast_easy'] and conditions['fast_easy'] in condition_feedback and category in condition_feedback[conditions['fast_easy']]:
                                easy_vals.append(condition_feedback[conditions['fast_easy']][category])
                            if conditions['slow_easy'] and conditions['slow_easy'] in condition_feedback and category in condition_feedback[conditions['slow_easy']]:
                                easy_vals.append(condition_feedback[conditions['slow_easy']][category])
                            
                            hard_vals = []
                            if conditions['fast_hard'] and conditions['fast_hard'] in condition_feedback and category in condition_feedback[conditions['fast_hard']]:
                                hard_vals.append(condition_feedback[conditions['fast_hard']][category])
                            if conditions['slow_hard'] and conditions['slow_hard'] in condition_feedback and category in condition_feedback[conditions['slow_hard']]:
                                hard_vals.append(condition_feedback[conditions['slow_hard']][category])
                            
                            if easy_vals and hard_vals:
                                easy_avg = sum(easy_vals) / len(easy_vals)
                                hard_avg = sum(hard_vals) / len(hard_vals)
                                complexity_effect = hard_avg - easy_avg
                        
                        if can_calculate_interaction and all(category in condition_feedback[conditions[k]] for k in ['fast_easy', 'fast_hard', 'slow_easy', 'slow_hard']):
                            fast_easy_val = condition_feedback[conditions['fast_easy']][category]
                            fast_hard_val = condition_feedback[conditions['fast_hard']][category]
                            slow_easy_val = condition_feedback[conditions['slow_easy']][category]
                            slow_hard_val = condition_feedback[conditions['slow_hard']][category]
                            
                            fast_diff = fast_hard_val - fast_easy_val
                            slow_diff = slow_hard_val - slow_easy_val
                            interaction_effect = fast_diff - slow_diff
                        
                        effect_labels = []
                        effect_values = []
                        
                        if can_calculate_latency:
                            effect_labels.append('Latency\nEffect')
                            effect_values.append(latency_effect)
                        
                        if can_calculate_complexity:
                            effect_labels.append('Complexity\nEffect')
                            effect_values.append(complexity_effect)
                        
                        if can_calculate_interaction:
                            effect_labels.append('Interaction\nEffect')
                            effect_values.append(interaction_effect)
                        
                        effect_colors = []
                        for effect in effect_values:
                            if effect > 0.5:  # Meaningful positive effect
                                effect_colors.append('#1a9850')  # Green
                            elif effect < -0.5:  # Meaningful negative effect
                                effect_colors.append('#d73027')  # Red
                            else:  # Small or no effect
                                effect_colors.append('#878787')  # Gray
                        
                        bars = ax_effects.barh(effect_labels, effect_values, color=effect_colors, alpha=0.7)
                        
                        ax_effects.axvline(x=0, color='black', linestyle='-', alpha=0.7)
                        
                        for bar in bars:
                            width = bar.get_width()
                            alignment = 'left' if width < 0 else 'right'
                            xpos = width - 0.1 if width < 0 else width + 0.1
                            ax_effects.annotate(f'{width:.2f}',
                                            xy=(width, bar.get_y() + bar.get_height()/2),
                                            xytext=(5 * (-1 if width < 0 else 1), 0),
                                            textcoords="offset points",
                                            ha=alignment, va='center',
                                            fontsize=10)
                        
                        ax_effects.set_title('Main Effects', fontsize=12, fontweight='bold')
                        ax_effects.set_xlabel('Effect Size (Rating Points)', fontsize=10)
                        
                        max_effect = max([abs(e) for e in effect_values]) if effect_values else 1
                        ax_effects.set_xlim(-max_effect-0.5, max_effect+0.5)
                        
                        effects_text = ""
                        
                        if can_calculate_latency and abs(latency_effect) > 0.5:
                            direction = "increases" if latency_effect > 0 else "decreases"
                            effects_text += f"• Higher latency {direction} trust\n"
                            
                        if can_calculate_complexity and abs(complexity_effect) > 0.5:
                            direction = "increases" if complexity_effect > 0 else "decreases"
                            effects_text += f"• Higher complexity {direction} trust\n"
                            
                        if can_calculate_interaction and abs(interaction_effect) > 0.5:
                            effects_text += f"• Factors interact with each other\n"
                        
                        if effects_text:
                            y_pos = 0.12 if len(effects_text.split('\n')) <= 2 else 0.05
                            ax_effects.text(0.02, y_pos, effects_text,
                                transform=ax_effects.transAxes, fontsize=9,
                                bbox=dict(boxstyle='round,pad=0.3', facecolor='#f8f9fa', alpha=0.9))
                        
                        ax_effects.grid(axis='x', linestyle='--', alpha=0.7)
                    else:
                        ax_effects.text(0.5, 0.5, "Insufficient data\nto calculate effects",
                                      ha='center', va='center', transform=ax_effects.transAxes,
                                      fontsize=10, style='italic')
                        ax_effects.axis('off')
                else:
                    ax_effects.text(0.5, 0.5, "Insufficient data\nto calculate effects",
                                  ha='center', va='center', transform=ax_effects.transAxes,
                                  fontsize=10, style='italic')
                    ax_effects.axis('off')
            
            fig.text(0.5, 0.01, 
                    'Research Question: "How does perceived trust in AI-generated health advice vary as a function of\nresponse latency (fast vs. slow) and cognitive complexity (easy vs. hard)?"', 
                    ha='center', fontsize=10, style='italic',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='#f8f9fa', alpha=0.8))
            
            fig.text(0.5, 0.005, 
                    'Note: Visual representation of effects without formal significance testing.\nFormal statistical analysis (ANOVA) would be required to establish significance.', 
                    ha='center', fontsize=8, style='italic')
            
            plt.tight_layout(rect=[0, 0.03, 1, 0.98])
            
            output_path = os.path.join(self.cache_dir, f"trust_metrics_comparison.png")
            plt.savefig(output_path, dpi=100, bbox_inches='tight')
            plt.close(fig)
            
            return output_path
            
        except Exception as e:
            log_print(f"Error creating trust metrics comparison: {str(e)}")
            return None
    
    def _create_trust_ratings_over_time(self, report_data, timestamp):
        
        log_print("Trust ratings over time visualization not implemented - requires historical data")
        return None
    
    def _upload_image(self, image_path, image_name):
        if not self.imgbb_api_key:
            log_print("ImgBB API key not configured. Cannot upload image.")
            return None
        
        try:
            with open(image_path, "rb") as file:
                image_data = base64.b64encode(file.read())
            
            consistent_name = f"{image_name}"
            
            expiration = 7 * 24 * 60 * 60  # 7 days in seconds
            
            url = "https://api.imgbb.com/1/upload"
            payload = {
                "key": self.imgbb_api_key,
                "image": image_data,
                "name": consistent_name,
                "expiration": expiration
            }
            
            response = requests.post(url, payload)
            
            if response.status_code == 200:
                json_data = response.json()
                if json_data.get("success", False):
                    image_url = json_data["data"]["url"]
                    delete_url = json_data["data"].get("delete_url", "Not available")
                    log_print(f"Successfully uploaded image: {image_name}")
                    log_print(f"Image delete URL: {delete_url}")
                    log_print(f"Image will auto-expire in 7 days")
                    return image_url
                else:
                    log_print(f"Failed to upload image: {json_data.get('error', {}).get('message', 'Unknown error')}")
            else:
                log_print(f"Failed to upload image. Status code: {response.status_code}")
            
            return None
            
        except Exception as e:
            log_print(f"Error uploading image to ImgBB: {str(e)}")
            return None
    
    def get_image_as_base64(self, image_path):
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode()
        except Exception as e:
            log_print(f"Error encoding image to base64: {str(e)}")
            return None
    
    def cleanup_old_cache_files(self, max_age_days=30):
        if not os.path.exists(self.cache_dir):
            log_print(f"Cache directory {self.cache_dir} does not exist")
            return 0
            
        try:
            now = datetime.now()
            count = 0
            
            essential_charts = [
                "completion_chart.png",
                "scenario_chart.png",
                "design_chart.png"
            ]
            
            for file_name in os.listdir(self.cache_dir):
                file_path = os.path.join(self.cache_dir, file_name)
                
                if not os.path.isfile(file_path):
                    continue
                    
                if file_name in essential_charts:
                    continue
                
                mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                age_days = (now - mtime).days
                
                if age_days > max_age_days or (not file_name in essential_charts and "_" in file_name):
                    os.remove(file_path)
                    count += 1
                    log_print(f"Deleted cache file: {file_name} (age: {age_days} days)")
            
            return count
            
        except Exception as e:
            log_print(f"Error cleaning up cache files: {str(e)}")
            return 0
metrics_visualizer = MetricsVisualizer() 