#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Local Agent for AI Smart Laptop Management

This module serves as the core application that manages the workflow between
user input, system sensors, Ollama LLM, and action execution.
"""

import json
import logging
import os
import sys
import time
from typing import Dict, List, Any, Optional, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('laptop_agent.log')
    ]
)
logger = logging.getLogger('local_agent')

# Import other modules
from data_processing import DataProcessor
from system_sensors import SystemSensorManager
from action_execution import ActionExecutor
from ollama_interface import OllamaInterface


class LocalAgent:
    """Core agent that orchestrates the AI laptop management workflow."""
    
    def __init__(self, config_path: str = 'config.json'):
        """Initialize the local agent with configuration.
        
        Args:
            config_path: Path to the configuration file
        """
        self.config = self._load_config(config_path)
        
        # Initialize components
        self.data_processor = DataProcessor()
        self.sensor_manager = SystemSensorManager()
        self.action_executor = ActionExecutor()
        
        # Initialize Ollama interface with the configured model
        model_name = self.config.get('llm_model', 'llama2')
        self.ollama = OllamaInterface(model_name)
        
        logger.info(f"Local Agent initialized with model: {model_name}")
    
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from JSON file.
        
        Args:
            config_path: Path to the configuration file
            
        Returns:
            Dict containing configuration parameters
        """
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    return json.load(f)
            else:
                # Default configuration
                default_config = {
                    'llm_model': 'llama2',
                    'api_base': 'http://localhost:11434',
                    'system_check_interval': 60,  # seconds
                    'log_level': 'INFO'
                }
                # Save default config
                with open(config_path, 'w') as f:
                    json.dump(default_config, f, indent=4)
                return default_config
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            return {}
    
    def process_user_input(self, user_input: str) -> Dict:
        """Process user input and generate a response.
        
        Args:
            user_input: The command or request from the user
            
        Returns:
            Dict containing the response and any actions to execute
        """
        try:
            # Collect system data
            system_data = self.sensor_manager.collect_data()
            
            # Process the data
            processed_data = self.data_processor.process(
                user_input=user_input,
                system_data=system_data
            )
            
            # Send to Ollama and get response
            llm_response = self.ollama.generate_response(processed_data)
            
            # Parse the response to determine actions
            actions = self.data_processor.extract_actions(llm_response)
            
            # Execute actions
            results = self.action_executor.execute_actions(actions)
            
            return {
                'response': llm_response,
                'actions': actions,
                'results': results
            }
        except Exception as e:
            logger.error(f"Error processing user input: {e}")
            return {
                'response': f"Error: {str(e)}",
                'actions': [],
                'results': []
            }
    
    def run_cli(self):
        """Run the agent in command-line interface mode."""
        print("=== AI Smart Laptop Management ===\n")
        print("Type 'exit' or 'quit' to end the session.\n")
        
        while True:
            try:
                user_input = input("\n> ")
                
                if user_input.lower() in ['exit', 'quit']:
                    print("Exiting...")
                    break
                
                result = self.process_user_input(user_input)
                print(f"\nResponse: {result['response']}")
                
                if result['actions']:
                    print("\nActions taken:")
                    for i, action in enumerate(result['actions']):
                        print(f"{i+1}. {action['description']}")
                        print(f"   Result: {result['results'][i]}")
            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                print(f"\nError: {str(e)}")
    
    def run_background_service(self):
        """Run the agent as a background service that periodically checks system state."""
        interval = self.config.get('system_check_interval', 60)
        logger.info(f"Starting background service with {interval}s check interval")
        
        try:
            while True:
                # Collect system data
                system_data = self.sensor_manager.collect_data()
                
                # Check if any automatic actions are needed
                if self.data_processor.should_take_action(system_data):
                    processed_data = self.data_processor.process(
                        user_input="",  # No user input in background mode
                        system_data=system_data
                    )
                    
                    llm_response = self.ollama.generate_response(processed_data)
                    actions = self.data_processor.extract_actions(llm_response)
                    
                    if actions:
                        logger.info(f"Taking automatic actions: {actions}")
                        self.action_executor.execute_actions(actions)
                
                time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("Background service stopped by user")
        except Exception as e:
            logger.error(f"Background service error: {e}")


def main():
    """Main entry point for the application."""
    import argparse
    
    parser = argparse.ArgumentParser(description='AI Smart Laptop Management')
    parser.add_argument('--config', type=str, default='config.json',
                        help='Path to configuration file')
    parser.add_argument('--background', action='store_true',
                        help='Run as a background service')
    
    args = parser.parse_args()
    
    agent = LocalAgent(config_path=args.config)
    
    if args.background:
        agent.run_background_service()
    else:
        agent.run_cli()


if __name__ == '__main__':
    main()