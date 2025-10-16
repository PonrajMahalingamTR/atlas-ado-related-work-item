#!/usr/bin/env python3
"""
Configuration settings for OpenArena integration
"""

import os
from typing import Optional
from .env_config import set_environment_variables

# Set environment variables from env_config.py
set_environment_variables()

class OpenArenaConfig:
    """Configuration class for OpenArena integration"""
    
    def __init__(self):
        # ESSO token for authentication
        self.esso_token = os.getenv('OPENARENA_ESSO_TOKEN')
        
        # WebSocket base URL
        self.websocket_base_url = os.getenv('OPENARENA_WEBSOCKET_URL')
        
        # Workflow IDs for different models
        self.workflow_ids = {
            'claude41opus': os.getenv('OPENARENA_CLAUDE41OPUS_WORKFLOW_ID'),
            'gpt5': os.getenv('OPENARENA_GPT5_WORKFLOW_ID'),
            'gemini25pro': os.getenv('OPENARENA_GEMINI25PRO_WORKFLOW_ID'),
            'llama3_70b': os.getenv('OPENARENA_LLAMA3_70B_WORKFLOW_ID'),
            # Azure OpenAI models via OpenArena
            'gpt4': os.getenv('OPENARENA_GPT4_WORKFLOW_ID'),
            'gpt4_turbo': os.getenv('OPENARENA_GPT4_TURBO_WORKFLOW_ID'),
            'gpt35': os.getenv('OPENARENA_GPT35_WORKFLOW_ID'),
            # New Azure OpenAI workflow
            'azure_openai': os.getenv('OPENARENA_AZURE_OPENAI_WORKFLOW_ID')
        }
        
        # Additional configuration
        self.max_retries = int(os.getenv('OPENARENA_MAX_RETRIES', '3'))
        self.timeout = int(os.getenv('OPENARENA_TIMEOUT', '30'))
        self.max_message_size = int(os.getenv('OPENARENA_MAX_MESSAGE_SIZE', '100000'))
    
    def get_workflow_id(self, model: str) -> str:
        """Get workflow ID for a specific model"""
        return self.workflow_ids.get(model, self.workflow_ids['gemini25pro'])
    
    def validate(self) -> bool:
        """Validate that required configuration is present"""
        if not self.esso_token:
            return False
        if not self.websocket_base_url:
            return False
        return True

def get_config() -> OpenArenaConfig:
    """Get the OpenArena configuration instance"""
    return OpenArenaConfig()
