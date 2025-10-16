#!/usr/bin/env python3
"""
Environment configuration for OpenArena integration
Configuration values are defined directly in this file and set as environment variables
"""

import os

# OpenArena Configuration
# Configuration values are defined directly in this file

# ESSO Token for OpenArena authentication (with 'Bearer' prefix)
# Get this from your OpenArena platform or set via environment variable
OPENARENA_ESSO_TOKEN = os.getenv('OPENARENA_ESSO_TOKEN', 'your_esso_token_here')

# WebSocket base URL for OpenArena
OPENARENA_WEBSOCKET_URL="wss://wymocw0zke.execute-api.us-east-1.amazonaws.com/prod"

# Workflow IDs for different models (replace with actual workflow IDs from OpenArena)
OPENARENA_CLAUDE41OPUS_WORKFLOW_ID="7953b63f-b450-4797-bf92-17c07ffa9480"
OPENARENA_GPT5_WORKFLOW_ID="637c5ae6-6eb5-4bc6-b8d1-1bb58c002172"
OPENARENA_GEMINI25PRO_WORKFLOW_ID="62b8e839-99ec-4064-890a-be66379f88e6"
OPENARENA_LLAMA3_70B_WORKFLOW_ID="c8238610-55b2-49fa-8b3f-2e57ba6764ca"

# Add Azure OpenAI workflow IDs (create these in OpenArena platform)
OPENARENA_GPT4_WORKFLOW_ID="your-gpt4-workflow-id"
OPENARENA_GPT4_TURBO_WORKFLOW_ID="your-gpt4-turbo-workflow-id"
OPENARENA_GPT35_WORKFLOW_ID="your-gpt35-workflow-id"

# New Azure OpenAI workflow
OPENARENA_AZURE_OPENAI_WORKFLOW_ID="4410d1da-6741-443d-8c7c-c9255c27222d"

# Connection settings
OPENARENA_MAX_RETRIES = 3
OPENARENA_TIMEOUT = 120  # Increased to 2 minutes for large datasets
# Increased WebSocket message size limit to handle larger work item datasets
# 1MB should handle most analysis scenarios while staying within reasonable bounds
OPENARENA_MAX_MESSAGE_SIZE = 1000000

# Fallback settings for when messages are still too large
OPENARENA_SAFE_MESSAGE_SIZE = 500000  # 500KB safe size for guaranteed delivery
OPENARENA_MIN_MESSAGE_SIZE = 100000   # 100KB minimum fallback size

# Debug settings
OPENARENA_DEBUG_FULL_QUERY = "false"  # Set to "true" to log full query content
OPENARENA_DEBUG_FULL_RESPONSE = "false"  # Set to "true" to log full response content

# Azure DevOps Configuration (existing)
# Get these from your Azure DevOps organization or set via environment variables
AZURE_DEVOPS_PAT = os.getenv('AZURE_DEVOPS_PAT', 'your_azure_devops_pat_here')
AZURE_DEVOPS_ORG_URL = os.getenv('AZURE_DEVOPS_ORG_URL', 'https://dev.azure.com/your-organization')
AZURE_DEVOPS_PROJECT = os.getenv('AZURE_DEVOPS_PROJECT', 'your-project-name')

def set_environment_variables():
    """Set environment variables programmatically"""
    import os
    
    os.environ['OPENARENA_ESSO_TOKEN'] = OPENARENA_ESSO_TOKEN
    os.environ['OPENARENA_WEBSOCKET_URL'] = OPENARENA_WEBSOCKET_URL
    os.environ['OPENARENA_CLAUDE41OPUS_WORKFLOW_ID'] = OPENARENA_CLAUDE41OPUS_WORKFLOW_ID
    os.environ['OPENARENA_GPT5_WORKFLOW_ID'] = OPENARENA_GPT5_WORKFLOW_ID
    os.environ['OPENARENA_GEMINI25PRO_WORKFLOW_ID'] = OPENARENA_GEMINI25PRO_WORKFLOW_ID
    os.environ['OPENARENA_LLAMA3_70B_WORKFLOW_ID'] = OPENARENA_LLAMA3_70B_WORKFLOW_ID
    os.environ['OPENARENA_AZURE_OPENAI_WORKFLOW_ID'] = OPENARENA_AZURE_OPENAI_WORKFLOW_ID
    os.environ['OPENARENA_MAX_RETRIES'] = str(OPENARENA_MAX_RETRIES)
    os.environ['OPENARENA_TIMEOUT'] = str(OPENARENA_TIMEOUT)
    os.environ['OPENARENA_MAX_MESSAGE_SIZE'] = str(OPENARENA_MAX_MESSAGE_SIZE)
    os.environ['OPENARENA_SAFE_MESSAGE_SIZE'] = str(OPENARENA_SAFE_MESSAGE_SIZE)
    os.environ['OPENARENA_MIN_MESSAGE_SIZE'] = str(OPENARENA_MIN_MESSAGE_SIZE)
    os.environ['OPENARENA_DEBUG_FULL_QUERY'] = OPENARENA_DEBUG_FULL_QUERY
    os.environ['OPENARENA_DEBUG_FULL_RESPONSE'] = OPENARENA_DEBUG_FULL_RESPONSE
    
    # Set Azure DevOps environment variables
    os.environ['AZURE_DEVOPS_PAT'] = AZURE_DEVOPS_PAT
    os.environ['AZURE_DEVOPS_ORG_URL'] = AZURE_DEVOPS_ORG_URL
    os.environ['AZURE_DEVOPS_PROJECT'] = AZURE_DEVOPS_PROJECT
