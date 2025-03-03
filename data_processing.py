#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Data Processing Module for AI Smart Laptop Management

This module handles the transformation of raw sensor data into a format
suitable for the LLM, including data cleaning, normalization, and feature extraction.
"""

import json
import logging
from typing import Dict, List, Any, Optional, Union

logger = logging.getLogger('data_processing')


class DataProcessor:
    """Handles processing of system data and user input for LLM consumption."""
    
    def __init__(self):
        """Initialize the data processor."""
        self.threshold_config = {
            'cpu_usage': 80,  # Percentage
            'memory_usage': 80,  # Percentage
            'disk_usage': 90,  # Percentage
            'battery_low': 20,  # Percentage
        }
    
    def process(self, user_input: str, system_data: Dict) -> Dict:
        """Process user input and system data into a format for the LLM.
        
        Args:
            user_input: The command or request from the user
            system_data: Dictionary containing system sensor data
            
        Returns:
            Processed data ready for LLM consumption
        """
        # Clean and normalize the data
        cleaned_data = self._clean_data(system_data)
        
        # Extract relevant features
        features = self._extract_features(cleaned_data)
        
        # Combine with user input
        prompt = self._create_prompt(user_input, features)
        
        return {
            'prompt': prompt,
            'features': features,
            'raw_data': cleaned_data
        }
    
    def _clean_data(self, data: Dict) -> Dict:
        """Clean and normalize the raw system data.
        
        Args:
            data: Raw system data from sensors
            
        Returns:
            Cleaned and normalized data
        """
        cleaned = {}
        
        # Handle missing or invalid values
        for key, value in data.items():
            if key in ['cpu_usage', 'memory_usage', 'disk_usage'] and isinstance(value, (int, float)):
                # Ensure percentages are between 0-100
                cleaned[key] = max(0, min(100, value))
            elif key == 'running_processes' and isinstance(value, list):
                # Limit to top processes by resource usage
                cleaned[key] = sorted(value, key=lambda x: x.get('cpu_usage', 0), reverse=True)[:10]
            elif key == 'system_logs' and isinstance(value, list):
                # Filter to recent and relevant logs
                cleaned[key] = [log for log in value if log.get('level') in ['ERROR', 'WARNING']][:5]
            else:
                cleaned[key] = value
        
        return cleaned
    
    def _extract_features(self, data: Dict) -> Dict:
        """Extract relevant features from the cleaned data.
        
        Args:
            data: Cleaned system data
            
        Returns:
            Dictionary of extracted features
        """
        features = {}
        
        # System resource usage
        features['high_cpu'] = data.get('cpu_usage', 0) > self.threshold_config['cpu_usage']
        features['high_memory'] = data.get('memory_usage', 0) > self.threshold_config['memory_usage']
        # Handle disk_usage which is a dictionary with a 'percent' key
        if isinstance(data.get('disk_usage'), dict):
            features['high_disk'] = data.get('disk_usage', {}).get('percent', 0) > self.threshold_config['disk_usage']
        else:
            features['high_disk'] = False
        
        # Battery status
        if 'battery' in data:
            features['low_battery'] = data['battery'].get('percentage', 100) < self.threshold_config['battery_low']
            features['is_charging'] = data['battery'].get('is_charging', False)
        else:
            features['low_battery'] = False
            features['is_charging'] = True  # Assume desktop or plugged in
        
        # System state
        features['has_errors'] = any(log.get('level') == 'ERROR' for log in data.get('system_logs', []))
        features['has_warnings'] = any(log.get('level') == 'WARNING' for log in data.get('system_logs', []))
        
        # Resource-intensive processes
        if 'running_processes' in data and data['running_processes']:
            top_process = data['running_processes'][0]
            features['top_process'] = {
                'name': top_process.get('name', 'unknown'),
                'cpu_usage': top_process.get('cpu_usage', 0),
                'memory_usage': top_process.get('memory_usage', 0)
            }
        
        return features
    
    def _create_prompt(self, user_input: str, features: Dict) -> str:
        """Create a prompt for the LLM based on user input and features.
        
        Args:
            user_input: The command or request from the user
            features: Extracted system features
            
        Returns:
            Formatted prompt string for the LLM
        """
        # Start with system context
        system_context = "You are an AI assistant managing a Windows laptop. "
        
        # Add system state information
        system_state = []
        if features.get('high_cpu'):
            system_state.append("CPU usage is high")
        if features.get('high_memory'):
            system_state.append("Memory usage is high")
        if features.get('high_disk'):
            system_state.append("Disk usage is high")
        if features.get('low_battery'):
            if features.get('is_charging'):
                system_state.append("Battery is low but charging")
            else:
                system_state.append("Battery is low and not charging")
        if features.get('has_errors'):
            system_state.append("System has error logs")
        if features.get('has_warnings'):
            system_state.append("System has warning logs")
        
        if system_state:
            system_context += "Current system state: " + ", ".join(system_state) + ". "
        
        # Add top process if available
        if 'top_process' in features:
            top = features['top_process']
            system_context += f"The most resource-intensive process is {top['name']} "
            system_context += f"using {top['cpu_usage']}% CPU and {top['memory_usage']}% memory. "
        
        # Combine with user input
        if user_input:
            prompt = f"{system_context}\n\nUser request: {user_input}\n\n"
            prompt += "Provide a helpful response and suggest actions if needed. "
            prompt += "For actions, use the format ACTION: [action_name] with [parameters]."
        else:
            # For background monitoring
            prompt = f"{system_context}\n\n"
            prompt += "Based on the system state, suggest any actions that should be taken. "
            prompt += "Use the format ACTION: [action_name] with [parameters]."
        
        return prompt
    
    def extract_actions(self, llm_response: str) -> List[Dict]:
        """Extract action directives from the LLM response.
        
        Args:
            llm_response: The response from the LLM
            
        Returns:
            List of action dictionaries
        """
        actions = []
        lines = llm_response.split('\n')
        
        for line in lines:
            if line.startswith('ACTION:'):
                # Parse the action directive
                action_text = line[7:].strip()  # Remove 'ACTION: ' prefix
                
                # Extract action name and parameters
                if ' with ' in action_text:
                    action_name, params_text = action_text.split(' with ', 1)
                    # Parse parameters
                    params = {}
                    try:
                        # Try to parse as JSON if it looks like it
                        if params_text.startswith('{') and params_text.endswith('}'):
                            params = json.loads(params_text)
                        else:
                            # Simple key-value parsing
                            for param in params_text.split(','):
                                if '=' in param:
                                    key, value = param.split('=', 1)
                                    params[key.strip()] = value.strip()
                    except Exception as e:
                        logger.warning(f"Failed to parse action parameters: {e}")
                        params = {'raw_params': params_text}
                else:
                    action_name = action_text
                    params = {}
                
                actions.append({
                    'name': action_name.strip(),
                    'parameters': params,
                    'description': action_text
                })
        
        return actions
    
    def should_take_action(self, system_data: Dict) -> bool:
        """Determine if automatic action should be taken based on system data.
        
        Args:
            system_data: Dictionary containing system sensor data
            
        Returns:
            Boolean indicating if action should be taken
        """
        # Clean the data
        cleaned_data = self._clean_data(system_data)
        
        # Extract features
        features = self._extract_features(cleaned_data)
        
        # Check for critical conditions
        critical_conditions = [
            features.get('high_cpu', False),
            features.get('high_memory', False),
            features.get('high_disk', False),
            features.get('low_battery', False) and not features.get('is_charging', True),
            features.get('has_errors', False)
        ]
        
        # Take action if any critical condition is met
        return any(critical_conditions)