#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Ollama Interface Module for AI Smart Laptop Management

This module handles communication with the Ollama API to send requests
and receive responses from the local LLM model.
"""

import json
import logging
import requests
from typing import Dict, List, Any, Optional, Union

logger = logging.getLogger('ollama_interface')


class OllamaInterface:
    """Interface for communicating with Ollama API."""
    
    def __init__(self, model_name: str, api_base: str = 'http://localhost:11434'):
        """Initialize the Ollama interface.
        
        Args:
            model_name: Name of the LLM model to use
            api_base: Base URL for the Ollama API
        """
        self.model_name = model_name
        self.api_base = api_base
        self.generate_endpoint = f"{api_base}/api/generate"
        
        logger.info(f"Initialized Ollama interface with model: {model_name}")
        
        # Verify connection to Ollama
        self._verify_connection()
    
    def _verify_connection(self) -> bool:
        """Verify connection to Ollama API.
        
        Returns:
            Boolean indicating if connection is successful
        """
        try:
            # Try to get list of models to verify connection
            response = requests.get(f"{self.api_base}/api/tags")
            response.raise_for_status()
            
            # Check if our model is available
            models = response.json().get('models', [])
            model_names = [model.get('name') for model in models]
            
            if self.model_name not in model_names:
                logger.warning(f"Model '{self.model_name}' not found in Ollama. Available models: {model_names}")
                logger.warning(f"You may need to pull the model using: ollama pull {self.model_name}")
            else:
                logger.info(f"Successfully connected to Ollama. Model '{self.model_name}' is available.")
            
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to connect to Ollama API: {e}")
            logger.error("Make sure Ollama is running and accessible at the configured API base URL.")
            return False
    
    def generate_response(self, data: Dict) -> str:
        """Generate a response from the LLM using the provided data.
        
        Args:
            data: Dictionary containing processed data and prompt
            
        Returns:
            String containing the LLM's response
        """
        try:
            # Prepare the request payload
            payload = {
                "model": self.model_name,
                "prompt": data['prompt'],
                "stream": False
            }
            
            # Send request to Ollama
            response = requests.post(self.generate_endpoint, json=payload)
            response.raise_for_status()
            
            # Extract and return the response text
            result = response.json()
            return result.get('response', '')
        except requests.exceptions.RequestException as e:
            error_msg = f"Error communicating with Ollama API: {e}"
            logger.error(error_msg)
            return f"Error: {error_msg}"
        except Exception as e:
            error_msg = f"Unexpected error generating response: {e}"
            logger.error(error_msg)
            return f"Error: {error_msg}"
    
    def get_model_info(self) -> Dict:
        """Get information about the current model.
        
        Returns:
            Dictionary containing model information
        """
        try:
            response = requests.get(f"{self.api_base}/api/show", params={"name": self.model_name})
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting model info: {e}")
            return {}


# For testing
if __name__ == '__main__':
    # Configure logging for standalone testing
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create Ollama interface
    ollama = OllamaInterface('llama3.2:1b')
    
    # Test generating a response
    test_data = {
        'prompt': 'What is the current state of my laptop?'
    }
    
    response = ollama.generate_response(test_data)
    print(f"\nResponse: {response}")