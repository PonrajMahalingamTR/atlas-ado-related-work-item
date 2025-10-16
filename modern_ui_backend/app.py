#!/usr/bin/env python3
"""
Azure DevOps AI Studio - Modern UI Backend

Flask backend to serve the modern React UI and provide API endpoints
for LLM analysis results with confidence scoring.
"""

import os
import sys
import json
import logging
import re
from datetime import datetime
from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS
import traceback

# Add the parent directory to the Python path to import from the main project
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.ado.ado_access import AzureDevOpsClient
from src.llm.ado_analysis_prompt import ADOWorkItemAnalysisPrompt
from src.openarena.websocket_client import OpenArenaWebSocketClient

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, 
            static_folder='../modern_ui/build',
            static_url_path='')
CORS(app)

# Global variables for client instances
ado_client = None
openarena_client = None

def load_analysis_data_from_gui(work_item_id):
    """Load analysis data from GUI if available."""
    try:
        import tempfile
        import json
        
        # Look for analysis data file created by GUI
        temp_dir = tempfile.gettempdir()
        analysis_file = os.path.join(temp_dir, f"ado_analysis_{work_item_id}.json")
        
        if os.path.exists(analysis_file):
            with open(analysis_file, 'r', encoding='utf-8') as f:
                analysis_data = json.load(f)
                logger.info(f"Successfully loaded analysis data from {analysis_file}")
                return analysis_data
        else:
            logger.info(f"No analysis data file found at {analysis_file}")
            return None
            
    except Exception as e:
        logger.error(f"Error loading analysis data from GUI: {e}")
        return None

def initialize_clients():
    """Initialize Azure DevOps and OpenArena clients."""
    global ado_client, openarena_client
    
    try:
        # Add src directory to Python path for imports
        import os
        src_path = os.path.join(os.path.dirname(__file__), '..', 'src')
        sys.path.insert(0, src_path)
        
        # Load environment variables first
        from openarena.config.env_config import set_environment_variables
        set_environment_variables()
        
        # Get Azure DevOps configuration from environment
        org_url = os.getenv('AZURE_DEVOPS_ORG_URL')
        pat = os.getenv('AZURE_DEVOPS_PAT')
        
        if org_url and pat:
            # Initialize Azure DevOps client with real data
            ado_client = AzureDevOpsClient(org_url, pat)
            logger.info(f"Azure DevOps client initialized successfully for {org_url}")
        else:
            logger.warning("Azure DevOps credentials not found in environment variables")
        
        # Initialize OpenArena client
        openarena_client = OpenArenaWebSocketClient()
        logger.info("OpenArena client initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize clients: {e}")
        # Fall back to mock data if real clients fail
        logger.info("Falling back to mock data due to client initialization failure")
        pass

@app.route('/')
def serve_react_app():
    """Serve the React application."""
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/analysis/<int:work_item_id>')
def serve_analysis_page(work_item_id):
    """Serve the React application for analysis page."""
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/work-item/<int:work_item_id>/related-items')
def get_related_work_items(work_item_id):
    """Get related work items for a specific work item (Step 1 of analysis)."""
    try:
        if not ado_client:
            initialize_clients()
        
        if not ado_client:
            return jsonify({'error': 'Azure DevOps client not available'}), 500
        
        # Get work item details
        work_item = ado_client.get_work_item(work_item_id)
        if not work_item:
            return jsonify({'error': 'Work item not found'}), 404
        
        # Get project name from configuration or environment
        project_name = os.getenv('AZURE_DEVOPS_PROJECT', 'Your Project Name')
        
        # Find related work items using the same logic as tkinter GUI
        related_items = []
        
        # Try different strategies, same as the GUI implementation
        try:
            # First try title keywords approach (most effective)
            related_items = ado_client.query_related_work_items_by_title_keywords(project_name, work_item)
            logger.info(f"Found {len(related_items)} related items using title keywords")
            
            if not related_items:
                # Fallback to general keywords approach
                related_items = ado_client.query_related_work_items_by_keywords(project_name, work_item)
                logger.info(f"Found {len(related_items)} related items using general keywords")
                
            if not related_items:
                # Fallback to basic relationship query
                related_items = ado_client.query_related_work_items(project_name, work_item.id)
                logger.info(f"Found {len(related_items)} related items using basic relationships")
                
        except Exception as search_error:
            logger.error(f"Error searching for related items: {search_error}")
            related_items = []
        
        # Convert to format expected by frontend
        formatted_items = []
        for item in related_items[:50]:  # Limit to 50 items for performance
            formatted_items.append({
                'id': item.id,
                'title': item.fields.get('System.Title', 'No Title'),
                'type': item.fields.get('System.WorkItemType', 'Unknown'),
                'state': item.fields.get('System.State', 'Unknown'),
                'assignedTo': item.fields.get('System.AssignedTo', {}).get('displayName', 'Unassigned') if isinstance(item.fields.get('System.AssignedTo'), dict) else str(item.fields.get('System.AssignedTo', 'Unassigned')),
                'areaPath': item.fields.get('System.AreaPath', ''),
                'iterationPath': item.fields.get('System.IterationPath', ''),
                'description': item.fields.get('System.Description', '')[:200] + '...' if item.fields.get('System.Description', '') else '',
                'createdDate': str(item.fields.get('System.CreatedDate', '')),
                'priority': item.fields.get('Microsoft.VSTS.Common.Priority', None)
            })
        
        return jsonify({
            'success': True,
            'relatedWorkItems': formatted_items,
            'totalFound': len(formatted_items),
            'selectedWorkItem': {
                'id': work_item.id,
                'title': work_item.fields.get('System.Title', 'No Title'),
                'type': work_item.fields.get('System.WorkItemType', 'Unknown'),
                'state': work_item.fields.get('System.State', 'Unknown'),
                'assignedTo': work_item.fields.get('System.AssignedTo', {}).get('displayName', 'Unassigned') if isinstance(work_item.fields.get('System.AssignedTo'), dict) else str(work_item.fields.get('System.AssignedTo', 'Unassigned')),
                'areaPath': work_item.fields.get('System.AreaPath', ''),
                'iterationPath': work_item.fields.get('System.IterationPath', ''),
                'description': work_item.fields.get('System.Description', '')
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting related work items: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/work-item/<int:work_item_id>/llm-analysis', methods=['POST'])
def run_llm_analysis(work_item_id):
    """Run LLM analysis with related work items (Step 2 of analysis)."""
    try:
        data = request.get_json()
        related_items = data.get('relatedWorkItems', [])
        
        if not ado_client:
            initialize_clients()
        
        if not ado_client:
            return jsonify({'error': 'Azure DevOps client not available'}), 500
        
        # Get work item details
        work_item = ado_client.get_work_item(work_item_id)
        if not work_item:
            return jsonify({'error': 'Work item not found'}), 404
        
        # Convert related items back to work item objects for analysis
        all_work_items = []
        if related_items:
            for item_data in related_items:
                # Create a mock work item object with the necessary fields
                class MockWorkItem:
                    def __init__(self, item_data):
                        self.id = item_data['id']
                        self.fields = {
                            'System.Id': item_data['id'],
                            'System.Title': item_data.get('title', 'No Title'),
                            'System.WorkItemType': item_data.get('type', 'Unknown'),
                            'System.State': item_data.get('state', 'Unknown'),
                            'System.AssignedTo': item_data.get('assignedTo', 'Unassigned'),
                            'System.AreaPath': item_data.get('areaPath', ''),
                            'System.IterationPath': item_data.get('iterationPath', ''),
                            'System.Description': item_data.get('description', '')
                        }
                
                all_work_items.append(MockWorkItem(item_data))
        
        # Add the selected work item to the list
        all_work_items.append(work_item)
        
        # Get hierarchy information
        hierarchy = ado_client.get_work_item_hierarchy(work_item_id)
        
        # Perform LLM analysis
        analysis_prompt = ADOWorkItemAnalysisPrompt()
        system_prompt = analysis_prompt.create_system_prompt(work_item, all_work_items)
        
        logger.info(f"Running LLM analysis for work item {work_item_id} with {len(all_work_items)} related items")
        
        # Get LLM response from OpenArena
        if openarena_client:
            try:
                # Use the selected model workflow for analysis
                selected_model = 'claude-4-opus'  # Default to Claude 4 Opus
                workflow_id = openarena_client.workflow_ids.get(selected_model, 'gemini2pro')
                
                llm_response, cost_tracker = openarena_client.query_workflow(
                    workflow_id=workflow_id,
                    query=system_prompt,
                    is_persistence_allowed=False
                )
                
                logger.info(f"LLM analysis completed successfully")
                
            except Exception as llm_error:
                logger.error(f"LLM analysis error: {llm_error}")
                # Fallback to mock response for development
                llm_response = generate_mock_llm_response(work_item, all_work_items)
                cost_tracker = {}
        else:
            # Fallback to mock response for development
            logger.warning("OpenArena client not available, using mock response")
            llm_response = generate_mock_llm_response(work_item, all_work_items)
            cost_tracker = {}
        
        # Process LLM response to extract structured data
        analysis_data = process_llm_response(llm_response, work_item, all_work_items, hierarchy)
        
        # Update cost info with actual values from cost tracker
        if cost_tracker and isinstance(cost_tracker, dict) and cost_tracker.get('cost', 0) > 0:
            analysis_data['costInfo'] = {
                'cost': cost_tracker.get('cost', 0.0),
                'tokens': cost_tracker.get('tokens', 0),
                'model': selected_model,
                'timestamp': datetime.now().isoformat()
            }
        else:
            # Fallback to estimated values if no cost tracker or zero cost
            estimated_cost = 0.01 if selected_model == 'claude-4-opus' else 0.02
            estimated_tokens = 500 if selected_model == 'claude-4-opus' else 1000
            analysis_data['costInfo'] = {
                'cost': estimated_cost,
                'tokens': estimated_tokens,
                'model': selected_model,
                'timestamp': datetime.now().isoformat()
            }
        
        return jsonify({
            'success': True,
            'data': analysis_data
        })
        
    except Exception as e:
        logger.error(f"Error running LLM analysis: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/analysis/<int:work_item_id>')
def get_analysis_data(work_item_id):
    """Get LLM analysis data for a specific work item (legacy endpoint)."""
    try:
        # First, try to load analysis data from GUI if available
        analysis_data = load_analysis_data_from_gui(work_item_id)
        if analysis_data and analysis_data != {}:
            logger.info(f"Loaded analysis data from GUI for work item {work_item_id}")
            logger.info(f"Analysis data keys: {list(analysis_data.keys())}")
            return jsonify(analysis_data)
        else:
            logger.info(f"No valid analysis data found from GUI for work item {work_item_id}")
        
        # Initialize clients if not already done
        if not ado_client:
            initialize_clients()
        
        # Try to get real data first
        if ado_client:
            try:
                # Get work item details
                work_item = ado_client.get_work_item(work_item_id)
                if not work_item:
                    return jsonify({'error': 'Work item not found'}), 404
                
                # Get all work items for analysis
                all_work_items = ado_client.get_work_items()
                
                # Get hierarchy information
                hierarchy = ado_client.get_work_item_hierarchy(work_item_id)
                
                # Perform LLM analysis
                analysis_prompt = ADOWorkItemAnalysisPrompt()
                system_prompt = analysis_prompt.create_system_prompt(work_item, all_work_items)
                
                # Get LLM response from OpenArena
                if openarena_client:
                    # Use the selected model workflow for analysis
                    selected_model = getattr(openarena_client, 'current_model', 'gemini2pro')
                    workflow_id = openarena_client.workflow_ids.get(selected_model, 'gemini2pro')
                    
                    llm_response, cost_tracker = openarena_client.query_workflow(
                        workflow_id=workflow_id,
                        query=system_prompt,
                        is_persistence_allowed=False
                    )
                else:
                    # Fallback to mock response for development
                    llm_response = generate_mock_llm_response(work_item, all_work_items)
                    cost_tracker = {}
                
                # Process LLM response to extract structured data
                analysis_data = process_llm_response(llm_response, work_item, all_work_items, hierarchy)
                
                return jsonify(analysis_data)
                
            except Exception as ado_error:
                logger.warning(f"ADO client error, falling back to mock data: {ado_error}")
                # Fall back to mock data if ADO client fails
                analysis_data = get_mock_analysis_data(work_item_id)
                return jsonify(analysis_data)
        else:
            # Use mock data if no ADO client available
            analysis_data = get_mock_analysis_data(work_item_id)
            return jsonify(analysis_data)
        
    except Exception as e:
        logger.error(f"Error getting analysis data: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/mock')
def serve_mock_page():
    """Serve the mock demo page."""
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/mock')
def get_mock_data():
    """Get comprehensive mock analysis data for demo purposes."""
    return jsonify(get_comprehensive_mock_data())

@app.route('/api/work-items')
def get_work_items():
    """Get all work items."""
    try:
        if not ado_client:
            initialize_clients()
        
        if ado_client:
            try:
                work_items = ado_client.get_work_items()
                return jsonify(work_items)
            except Exception as ado_error:
                logger.warning(f"ADO client error: {ado_error}")
                return jsonify({'error': 'Unable to fetch work items from Azure DevOps'}), 500
        else:
            return jsonify({'error': 'Azure DevOps client not available'}), 500
        
    except Exception as e:
        logger.error(f"Error getting work items: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/work-item/<int:work_item_id>')
def get_work_item(work_item_id):
    """Get specific work item details."""
    try:
        if not ado_client:
            initialize_clients()
        
        if ado_client:
            try:
                work_item = ado_client.get_work_item(work_item_id)
                if not work_item:
                    return jsonify({'error': 'Work item not found'}), 404
                
                return jsonify(work_item)
            except Exception as ado_error:
                logger.warning(f"ADO client error: {ado_error}")
                return jsonify({'error': 'Unable to fetch work item from Azure DevOps'}), 500
        else:
            return jsonify({'error': 'Azure DevOps client not available'}), 500
        
    except Exception as e:
        logger.error(f"Error getting work item: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/config')
def get_config():
    """Get current configuration for connection fields."""
    try:
        config_data = {
            'azure_devops': {
                'org_url': '',
                'pat': '',
                'project': '',
            },
            'openarena': {
                'esso_token': '',
                'websocket_url': '',
                'workflow_id': '',
            },
            'auto_connect': False
        }
        
        # Load from ado_settings.txt if it exists
        config_file = os.path.join(os.path.dirname(__file__), '..', 'config', 'ado_settings.txt')
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if '=' in line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        if key == 'organization_url':
                            config_data['azure_devops']['org_url'] = value
                        elif key == 'pat':
                            config_data['azure_devops']['pat'] = value
                        elif key == 'project':
                            config_data['azure_devops']['project'] = value
                        elif key == 'auto_connect':
                            config_data['auto_connect'] = value.lower() == 'true'
        
        # Load OpenArena config from env_config.py
        try:
            from openarena.config.env_config import (
                OPENARENA_ESSO_TOKEN,
                OPENARENA_WEBSOCKET_URL,
                OPENARENA_GPT5_WORKFLOW_ID
            )
            config_data['openarena']['esso_token'] = OPENARENA_ESSO_TOKEN
            config_data['openarena']['websocket_url'] = OPENARENA_WEBSOCKET_URL
            config_data['openarena']['workflow_id'] = OPENARENA_GPT5_WORKFLOW_ID
        except ImportError:
            logger.warning("Could not import OpenArena config")
        
        return jsonify(config_data)
        
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/config', methods=['POST'])
def save_config():
    """Save updated configuration."""
    try:
        data = request.get_json()
        
        # Update ado_settings.txt
        config_file = os.path.join(os.path.dirname(__file__), '..', 'config', 'ado_settings.txt')
        config_lines = []
        
        # Read existing config
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config_lines = f.readlines()
        
        # Update or add values
        config_dict = {}
        for line in config_lines:
            line = line.strip()
            if '=' in line and not line.startswith('#'):
                key, value = line.split('=', 1)
                config_dict[key] = value
        
        # Update with new values
        if 'azure_devops' in data:
            if 'org_url' in data['azure_devops']:
                config_dict['organization_url'] = data['azure_devops']['org_url']
            if 'pat' in data['azure_devops']:
                config_dict['pat'] = data['azure_devops']['pat']
            if 'project' in data['azure_devops']:
                config_dict['project'] = data['azure_devops']['project']
        
        if 'auto_connect' in data:
            config_dict['auto_connect'] = str(data['auto_connect']).lower()
        
        # Preserve other existing values
        if 'team' not in config_dict:
            config_dict['team'] = 'Practical Law - Accessibility'
        if 'llm_work_item_limit' not in config_dict:
            config_dict['llm_work_item_limit'] = '1000'
        if 'llm_strategy' not in config_dict:
            config_dict['llm_strategy'] = 'general'
        if 'max_ado_work_item_limit' not in config_dict:
            config_dict['max_ado_work_item_limit'] = '19000'
        
        # Write updated config
        with open(config_file, 'w') as f:
            for key, value in config_dict.items():
                f.write(f"{key}={value}\n")
        
        # Update OpenArena config if provided (update env_config.py)
        if 'openarena' in data:
            env_config_file = os.path.join(os.path.dirname(__file__), '..', 'src', 'openarena', 'config', 'env_config.py')
            if os.path.exists(env_config_file):
                # Read current env_config.py
                with open(env_config_file, 'r') as f:
                    content = f.read()
                
                # Update values
                if 'esso_token' in data['openarena']:
                    # Replace ESSO token line
                    import re
                    content = re.sub(
                        r'OPENARENA_ESSO_TOKEN = ".*"',
                        f'OPENARENA_ESSO_TOKEN = "{data["openarena"]["esso_token"]}"',
                        content
                    )
                
                if 'websocket_url' in data['openarena']:
                    content = re.sub(
                        r'OPENARENA_WEBSOCKET_URL=".*"',
                        f'OPENARENA_WEBSOCKET_URL="{data["openarena"]["websocket_url"]}"',
                        content
                    )
                
                if 'workflow_id' in data['openarena']:
                    content = re.sub(
                        r'OPENARENA_GPT5_WORKFLOW_ID=".*"',
                        f'OPENARENA_GPT5_WORKFLOW_ID="{data["openarena"]["workflow_id"]}"',
                        content
                    )
                
                # Write updated env_config.py
                with open(env_config_file, 'w') as f:
                    f.write(content)
        
        return jsonify({'success': True, 'message': 'Configuration saved successfully'})
        
    except Exception as e:
        logger.error(f"Error saving configuration: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/connection-status')
def get_connection_status():
    """Get current connection status."""
    try:
        status = {
            'azure_devops': {
                'connected': ado_client is not None,
                'org_url': os.getenv('AZURE_DEVOPS_ORG_URL', ''),
                'project': os.getenv('AZURE_DEVOPS_PROJECT', ''),
                'last_check': datetime.now().isoformat()
            },
            'openarena': {
                'connected': openarena_client is not None,
                'websocket_url': os.getenv('OPENARENA_WEBSOCKET_URL', ''),
                'last_check': datetime.now().isoformat()
            }
        }
        
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"Error getting connection status: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# PHASE 1: USER PROFILE AND TEAM SELECTION APIs
# ============================================================================

@app.route('/api/user/profile')
def get_user_profile():
    """Get user profile with team preferences and settings."""
    try:
        # For now, return a mock profile - in production, this would come from a database
        profile = {
            'userId': 'current_user',
            'defaultTeamId': None,  # Will be set based on analysis
            'defaultTeamName': None,
            'lastSelectedTeam': None,
            'preferences': {
                'autoSelectTeam': True,
                'selectionMethod': 'hybrid',  # 'profile', 'workitem_count', 'hybrid'
                'showSelectionReason': True,
                'allowAutoSelectionOverride': True
            },
            'lastUpdated': datetime.now().isoformat()
        }
        
        return jsonify(profile)
        
    except Exception as e:
        logger.error(f"Error getting user profile: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/teams/workitem-counts')
def get_team_workitem_counts():
    """Get work item counts for each team for the current user."""
    try:
        if not ado_client:
            initialize_clients()
        
        if not ado_client:
            return jsonify({'error': 'Azure DevOps client not available'}), 500
        
        # Get project name from environment
        project_name = os.getenv('AZURE_DEVOPS_PROJECT', 'Your Project Name')
        
        # Get all teams in the project
        teams = ado_client.get_teams(project_name)
        
        # Mock user ID - in production, this would come from authentication
        user_id = 'current_user'
        
        team_counts = []
        
        for team in teams[:20]:  # Limit to first 20 teams for performance
            try:
                # Query work items assigned to this user in this team
                work_items = ado_client.query_work_items_by_team_and_user(
                    project_name, 
                    team.name, 
                    user_id
                )
                
                # Calculate activity metrics
                assigned_items = len([wi for wi in work_items if wi.fields.get('System.AssignedTo', {}).get('displayName', '').lower() == user_id.lower()])
                created_items = len([wi for wi in work_items if wi.fields.get('System.CreatedBy', {}).get('displayName', '').lower() == user_id.lower()])
                modified_items = len([wi for wi in work_items if wi.fields.get('System.ChangedBy', {}).get('displayName', '').lower() == user_id.lower()])
                
                # Get most recent activity
                recent_activity = None
                if work_items:
                    recent_dates = []
                    for wi in work_items:
                        if wi.fields.get('System.ChangedDate'):
                            recent_dates.append(wi.fields.get('System.ChangedDate'))
                    if recent_dates:
                        recent_activity = max(recent_dates).isoformat()
                
                team_counts.append({
                    'teamId': team.id,
                    'teamName': team.name,
                    'workItemCount': len(work_items),
                    'assignedItems': assigned_items,
                    'createdItems': created_items,
                    'modifiedItems': modified_items,
                    'recentActivity': recent_activity,
                    'isActive': len(work_items) > 0
                })
                
            except Exception as team_error:
                logger.warning(f"Error processing team {team.name}: {team_error}")
                continue
        
        # Sort by work item count descending
        team_counts.sort(key=lambda x: x['workItemCount'], reverse=True)
        
        return jsonify({
            'projectId': project_name,
            'userId': user_id,
            'teamCounts': team_counts,
            'totalTeams': len(teams),
            'analyzedTeams': len(team_counts),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting team work item counts: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/teams/auto-select', methods=['POST'])
def auto_select_team():
    """Automatically select the best team for the user based on analysis."""
    try:
        data = request.get_json()
        project_id = data.get('projectId', 'Your Project Name')
        user_id = data.get('userId', 'current_user')
        criteria = data.get('selectionCriteria', {})
        
        # Default criteria
        method = criteria.get('method', 'hybrid')
        time_range = criteria.get('timeRange', 'last_30_days')
        min_work_items = criteria.get('minWorkItems', 1)
        include_inactive = criteria.get('includeInactiveTeams', False)
        
        logger.info(f"Auto-selecting team for user {user_id} in project {project_id} using method: {method}")
        
        # Priority 1: Check user profile preference
        if method in ['profile', 'hybrid']:
            try:
                profile_response = get_user_profile()
                if profile_response[1] == 200:  # Success
                    profile_data = profile_response[0].get_json()
                    if profile_data.get('defaultTeamId'):
                        # Verify team is still active
                        if verify_team_active(project_id, profile_data['defaultTeamId']):
                            return jsonify({
                                'selectedTeamId': profile_data['defaultTeamId'],
                                'selectedTeamName': profile_data['defaultTeamName'],
                                'selectionReason': 'user_profile_preference',
                                'confidence': 0.95,
                                'alternatives': [],
                                'fallbackUsed': False,
                                'timestamp': datetime.now().isoformat()
                            })
            except Exception as profile_error:
                logger.warning(f"Error checking user profile: {profile_error}")
        
        # Priority 2: Analyze work item activity
        if method in ['workitem_count', 'hybrid']:
            try:
                counts_response = get_team_workitem_counts()
                if counts_response[1] == 200:  # Success
                    counts_data = counts_response[0].get_json()
                    team_counts = counts_data.get('teamCounts', [])
                    
                    # Filter by criteria
                    filtered_teams = [
                        team for team in team_counts 
                        if team['workItemCount'] >= min_work_items and 
                        (include_inactive or team['isActive'])
                    ]
                    
                    if filtered_teams:
                        best_team = filtered_teams[0]  # Already sorted by work item count
                        
                        # Calculate confidence score
                        confidence = calculate_confidence_score(best_team)
                        
                        # Get alternatives (next 2 teams)
                        alternatives = filtered_teams[1:3] if len(filtered_teams) > 1 else []
                        
                        return jsonify({
                            'selectedTeamId': best_team['teamId'],
                            'selectedTeamName': best_team['teamName'],
                            'selectionReason': 'highest_workitem_activity',
                            'confidence': confidence,
                            'alternatives': [
                                {
                                    'teamId': alt['teamId'],
                                    'teamName': alt['teamName'],
                                    'workItemCount': alt['workItemCount'],
                                    'reason': f'second_highest_count'
                                } for alt in alternatives
                            ],
                            'fallbackUsed': False,
                            'timestamp': datetime.now().isoformat()
                        })
            except Exception as counts_error:
                logger.warning(f"Error analyzing work item counts: {counts_error}")
        
        # Priority 3: Fallback to project default
        fallback_team = get_project_default_team(project_id)
        return jsonify({
            'selectedTeamId': fallback_team['teamId'],
            'selectedTeamName': fallback_team['teamName'],
            'selectionReason': 'project_default_fallback',
            'confidence': 0.5,
            'alternatives': [],
            'fallbackUsed': True,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in auto team selection: {e}")
        return jsonify({'error': str(e)}), 500

def verify_team_active(project_id, team_id):
    """Verify if a team is still active in the project."""
    try:
        if not ado_client:
            return False
        
        teams = ado_client.get_teams(project_id)
        return any(team.id == team_id for team in teams)
    except Exception:
        return False

def calculate_confidence_score(team_data):
    """Calculate confidence score for team selection."""
    try:
        base_score = min(team_data['workItemCount'] / 50, 1.0)  # Max at 50 items
        
        # Recent activity bonus
        if team_data.get('recentActivity'):
            try:
                recent_date = datetime.fromisoformat(team_data['recentActivity'].replace('Z', '+00:00'))
                days_since_activity = (datetime.now() - recent_date.replace(tzinfo=None)).days
                activity_bonus = max(0, (30 - days_since_activity) / 30)
            except:
                activity_bonus = 0
        else:
            activity_bonus = 0
        
        # Activity type diversity bonus
        activity_types = [
            team_data.get('assignedItems', 0),
            team_data.get('createdItems', 0),
            team_data.get('modifiedItems', 0)
        ]
        activity_diversity = len([x for x in activity_types if x > 0]) / 3
        
        confidence = min(base_score + (activity_bonus * 0.3) + (activity_diversity * 0.2), 1.0)
        return round(confidence, 2)
        
    except Exception:
        return 0.5  # Default confidence

def get_project_default_team(project_id):
    """Get the default team for a project."""
    try:
        if not ado_client:
            return {'teamId': 'default', 'teamName': 'Default Team'}
        
        teams = ado_client.get_teams(project_id)
        if teams:
            return {
                'teamId': teams[0].id,
                'teamName': teams[0].name
            }
        else:
            return {'teamId': 'default', 'teamName': 'Default Team'}
    except Exception:
        return {'teamId': 'default', 'teamName': 'Default Team'}

# ============================================================================
# PHASE 4: ANALYTICS AND USER PREFERENCES
# ============================================================================

@app.route('/api/analytics/team-selection', methods=['POST'])
def track_team_selection():
    """Track team selection events for analytics."""
    try:
        data = request.get_json()
        
        # Log the analytics event
        logger.info(f"📊 Team Selection Event: {data}")
        
        # In production, you would store this in a database
        # For now, we'll just log it and return success
        
        return jsonify({
            'success': True,
            'message': 'Analytics event tracked successfully',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error tracking team selection event: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/user/profile', methods=['PUT'])
def update_user_profile():
    """Update user profile preferences."""
    try:
        data = request.get_json()
        
        # In production, you would update the database
        # For now, we'll just log the update and return success
        
        logger.info(f"📝 User Profile Update: {data}")
        
        return jsonify({
            'success': True,
            'message': 'Profile updated successfully',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error updating user profile: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/connect', methods=['POST'])
def connect_services():
    """Connect to Azure DevOps and OpenArena with provided credentials."""
    try:
        data = request.get_json()
        results = {'success': True, 'connections': {}}
        
        # Connect to Azure DevOps
        if 'azure_devops' in data:
            ado_data = data['azure_devops']
            try:
                # Import here to avoid circular imports
                from ado.ado_access import AzureDevOpsClient
                
                global ado_client
                ado_client = AzureDevOpsClient(
                    ado_data.get('org_url'),
                    ado_data.get('pat')
                )
                
                # Test connection
                test_items = ado_client.get_work_items(max_items=1)
                if test_items:
                    results['connections']['azure_devops'] = {
                        'success': True,
                        'message': 'Connected successfully'
                    }
                    # Update environment variables
                    os.environ['AZURE_DEVOPS_ORG_URL'] = ado_data.get('org_url', '')
                    os.environ['AZURE_DEVOPS_PAT'] = ado_data.get('pat', '')
                    os.environ['AZURE_DEVOPS_PROJECT'] = ado_data.get('project', '')
                else:
                    results['connections']['azure_devops'] = {
                        'success': False,
                        'message': 'Connection test failed'
                    }
                    
            except Exception as e:
                results['connections']['azure_devops'] = {
                    'success': False,
                    'message': f'Connection failed: {str(e)}'
                }
                logger.error(f"Azure DevOps connection error: {e}")
        
        # Connect to OpenArena
        if 'openarena' in data:
            oa_data = data['openarena']
            try:
                from openarena.websocket_client import OpenArenaWebSocketClient
                
                # Update environment variables
                if 'esso_token' in oa_data:
                    os.environ['OPENARENA_ESSO_TOKEN'] = oa_data['esso_token']
                if 'websocket_url' in oa_data:
                    os.environ['OPENARENA_WEBSOCKET_URL'] = oa_data['websocket_url']
                if 'workflow_id' in oa_data:
                    os.environ['OPENARENA_GPT5_WORKFLOW_ID'] = oa_data['workflow_id']
                
                global openarena_client
                openarena_client = OpenArenaWebSocketClient()
                
                results['connections']['openarena'] = {
                    'success': True,
                    'message': 'Connected successfully'
                }
                
            except Exception as e:
                results['connections']['openarena'] = {
                    'success': False,
                    'message': f'Connection failed: {str(e)}'
                }
                logger.error(f"OpenArena connection error: {e}")
        
        return jsonify(results)
        
    except Exception as e:
        logger.error(f"Error connecting services: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

def process_llm_response(llm_response, selected_work_item, all_work_items, hierarchy):
    """Process LLM response using the advanced parser for accurate data extraction."""
    
    try:
        # Import the advanced parser
        from llm_response_parser import AdvancedLLMResponseParser, convert_parsed_analysis_to_dict
        
        # Create parser instance
        parser = AdvancedLLMResponseParser()
        
        # Parse the LLM response
        parsed_analysis = parser.parse_response(llm_response, all_work_items, selected_work_item)
        
        # Convert to the expected format
        analysis_data = convert_parsed_analysis_to_dict(parsed_analysis)
        
        # Combine all confidence levels into a single list for backward compatibility
        all_related_items = (
            analysis_data['highConfidenceItems'] + 
            analysis_data['mediumConfidenceItems'] + 
            analysis_data['lowConfidenceItems']
        )
        
        # Format selected work item
        selected_work_item_data = {
            'id': selected_work_item.id,
            'title': selected_work_item.fields.get('System.Title', 'No Title'),
            'type': selected_work_item.fields.get('System.WorkItemType', 'Unknown'),
            'state': selected_work_item.fields.get('System.State', 'Unknown'),
            'assignedTo': selected_work_item.fields.get('System.AssignedTo', {}).get('displayName', 'Unassigned'),
            'areaPath': selected_work_item.fields.get('System.AreaPath', ''),
            'iterationPath': selected_work_item.fields.get('System.IterationPath', ''),
            'description': selected_work_item.fields.get('System.Description', ''),
            'reason': selected_work_item.fields.get('System.Reason', '')
        }
        
        # Format hierarchy
        hierarchy_data = []
        if hierarchy and isinstance(hierarchy, dict):
            # Process hierarchy_path which contains the actual work items
            hierarchy_path = hierarchy.get('hierarchy_path', [])
            for item in hierarchy_path:
                hierarchy_data.append({
                    'id': item.id,
                    'title': item.fields.get('System.Title', 'No Title'),
                    'type': item.fields.get('System.WorkItemType', 'Unknown'),
                    'state': item.fields.get('System.State', 'Unknown'),
                    'assignedTo': item.fields.get('System.AssignedTo', {}).get('displayName', 'Unassigned'),
                    'areaPath': item.fields.get('System.AreaPath', ''),
                    'iterationPath': item.fields.get('System.IterationPath', ''),
                    'description': item.fields.get('System.Description', ''),
                    'reason': item.fields.get('System.Reason', '')
                })
        
        # Generate analysis insights with the extracted sections
        insights = generate_analysis_insights(
            all_related_items, 
            selected_work_item_data, 
            analysis_data['relationshipPatterns'], 
            analysis_data['riskAssessment'], 
            analysis_data['recommendations']
        )
        
        # Add detailed confidence breakdown to insights
        insights['confidenceBreakdown'] = {
            'high': len(analysis_data['highConfidenceItems']),
            'medium': len(analysis_data['mediumConfidenceItems']),
            'low': len(analysis_data['lowConfidenceItems'])
        }
        
        return {
            'selectedWorkItem': selected_work_item_data,
            'hierarchy': hierarchy_data,
            'relatedWorkItems': all_related_items,
            'analysisInsights': insights,
            'confidenceBreakdown': analysis_data['summary']
            # costInfo will be added by the calling function with actual values
        }
        
    except Exception as e:
        logger.error(f"Error in advanced LLM response parsing: {e}")
        # Fallback to the original simple parser
        return process_llm_response_fallback(llm_response, selected_work_item, all_work_items, hierarchy)

def process_llm_response_fallback(llm_response, selected_work_item, all_work_items, hierarchy):
    """Fallback LLM response parser using the original simple approach."""
    
    # Parse the LLM response to extract related work items with confidence scores
    related_work_items = []
    
    # This is a simplified parser - in production, you'd want more sophisticated parsing
    lines = llm_response.split('\n')
    current_section = None
    
    # Track current confidence level based on section headers
    current_confidence = 'low'  # Default confidence
    
    # Track analysis sections
    relationship_patterns = []
    risk_assessment = []
    recommendations = []
    
    for line in lines:
        line = line.strip()
        
        # Check for confidence section headers (handle both ## and ### formats)
        if 'HIGH CONFIDENCE RELATIONSHIPS' in line.upper() and ('##' in line or '###' in line):
            current_confidence = 'high'
            continue
        elif 'MEDIUM CONFIDENCE RELATIONSHIPS' in line.upper() and ('##' in line or '###' in line):
            current_confidence = 'medium'
            continue
        elif 'LOW CONFIDENCE RELATIONSHIPS' in line.upper() and ('##' in line or '###' in line):
            current_confidence = 'low'
            continue
        elif line.startswith('##') and 'RELATIONSHIPS' in line.upper():
            # Other relationship sections - default to low
            current_confidence = 'low'
            continue
        elif line.startswith('##') and not 'RELATIONSHIPS' in line.upper():
            # Other analysis sections - don't change confidence
            continue
        
        # Check for analysis section headers
        elif '## RELATIONSHIP PATTERNS ANALYSIS' in line.upper():
            current_section = 'patterns'
            continue
        elif '## RISK ASSESSMENT' in line.upper():
            current_section = 'risk'
            continue
        elif '## RECOMMENDATIONS' in line.upper():
            current_section = 'recommendations'
            continue
        elif line.startswith('##') and not 'RELATIONSHIPS' in line.upper():
            # Other analysis sections
            current_section = None
            continue
        
        # Process content based on current section
        if current_section == 'patterns' and line and not line.startswith('#'):
            relationship_patterns.append(line)
        elif current_section == 'risk' and line and not line.startswith('#'):
            risk_assessment.append(line)
        elif current_section == 'recommendations' and line and not line.startswith('#'):
            recommendations.append(line)
        
        # Also look for specific risk and recommendation patterns in any section
        if line and not line.startswith('#'):
            # Look for risk indicators
            if any(keyword in line.lower() for keyword in ['risk', 'blocking', 'conflict', 'dependency', 'issue', 'problem']):
                if current_section != 'risk':  # Don't duplicate if already in risk section
                    risk_assessment.append(line)
            
            # Look for recommendation indicators
            if any(keyword in line.lower() for keyword in ['recommend', 'suggest', 'action', 'consider', 'should', 'must', 'coordinate', 'review', 'audit']):
                if current_section != 'recommendations':  # Don't duplicate if already in recommendations section
                    recommendations.append(line)
        
        # Look for work item references in the response - handle multiple formats
        work_item_ids = []
        
        # Format 1: - **ID:** 12345 (from the images)
        if '- **ID:' in line and any(char.isdigit() for char in line):
            work_item_ids = re.findall(r'- \*\*ID:\s*(\d+)', line)
        
        # Format 2: ### 1. ID: 12345 (from the actual LLM response)
        elif '###' in line and 'ID:' in line and any(char.isdigit() for char in line):
            work_item_ids = re.findall(r'### \d+\. ID:\s*(\d+)', line)
        
        # Format 3: #12345 (legacy format)
        elif '#' in line and any(char.isdigit() for char in line):
            work_item_ids = re.findall(r'#(\d+)', line)
        
        # Format 4: Just numbers that look like work item IDs (6+ digits)
        elif any(char.isdigit() for char in line):
            # Look for 6+ digit numbers that could be work item IDs
            potential_ids = re.findall(r'\b(\d{6,})\b', line)
            work_item_ids = potential_ids
        
        for work_item_id in work_item_ids:
            work_item_id = int(work_item_id)
            
            # Find the work item in all_work_items
            related_item = next((item for item in all_work_items if item.id == work_item_id), None)
            
            if related_item and related_item.id != selected_work_item.id:
                # Use the current confidence level from section headers
                confidence = current_confidence
                
                # Determine relationship type
                relationship_type = determine_relationship_type(line, related_item, selected_work_item)
                
                # Extract reasoning
                reasoning = extract_reasoning(line, related_item, selected_work_item)
                
                related_work_items.append({
                    'id': related_item.id,
                    'title': related_item.fields.get('System.Title', 'No Title'),
                    'type': related_item.fields.get('System.WorkItemType', 'Unknown'),
                    'state': related_item.fields.get('System.State', 'Unknown'),
                    'assignedTo': related_item.fields.get('System.AssignedTo', {}).get('displayName', 'Unassigned'),
                    'areaPath': related_item.fields.get('System.AreaPath', ''),
                    'iterationPath': related_item.fields.get('System.IterationPath', ''),
                    'description': related_item.fields.get('System.Description', ''),
                    'confidence': confidence,
                    'relationshipType': relationship_type,
                    'reasoning': reasoning,
                    'lastUpdated': 'Recently'
                })
    
    # Remove duplicates
    seen_ids = set()
    unique_related_items = []
    for item in related_work_items:
        if item['id'] not in seen_ids:
            unique_related_items.append(item)
            seen_ids.add(item['id'])
    
    # Sort by confidence
    unique_related_items.sort(key=lambda x: {'high': 3, 'medium': 2, 'low': 1}.get(x['confidence'], 0), reverse=True)
    
    # Format selected work item
    selected_work_item_data = {
        'id': selected_work_item.id,
        'title': selected_work_item.fields.get('System.Title', 'No Title'),
        'type': selected_work_item.fields.get('System.WorkItemType', 'Unknown'),
        'state': selected_work_item.fields.get('System.State', 'Unknown'),
        'assignedTo': selected_work_item.fields.get('System.AssignedTo', {}).get('displayName', 'Unassigned'),
        'areaPath': selected_work_item.fields.get('System.AreaPath', ''),
        'iterationPath': selected_work_item.fields.get('System.IterationPath', ''),
        'description': selected_work_item.fields.get('System.Description', ''),
        'reason': selected_work_item.fields.get('System.Reason', '')
    }
    
    # Format hierarchy
    hierarchy_data = []
    if hierarchy and isinstance(hierarchy, dict):
        # Process hierarchy_path which contains the actual work items
        hierarchy_path = hierarchy.get('hierarchy_path', [])
        for item in hierarchy_path:
            hierarchy_data.append({
                'id': item.id,
                'title': item.fields.get('System.Title', 'No Title'),
                'type': item.fields.get('System.WorkItemType', 'Unknown'),
                'state': item.fields.get('System.State', 'Unknown'),
                'assignedTo': item.fields.get('System.AssignedTo', {}).get('displayName', 'Unassigned'),
                'areaPath': item.fields.get('System.AreaPath', ''),
                'iterationPath': item.fields.get('System.IterationPath', ''),
                'description': item.fields.get('System.Description', ''),
                'reason': item.fields.get('System.Reason', '')
            })
    
    # Generate analysis insights with the extracted sections
    insights = generate_analysis_insights(unique_related_items, selected_work_item_data, relationship_patterns, risk_assessment, recommendations)
    
    return {
        'selectedWorkItem': selected_work_item_data,
        'hierarchy': hierarchy_data,
        'relatedWorkItems': unique_related_items,
        'analysisInsights': insights
        # costInfo will be added by the calling function with actual values
    }

def determine_confidence_score(line, related_item, selected_work_item):
    """Determine confidence score based on context analysis."""
    line_lower = line.lower()
    
    # High confidence indicators
    high_indicators = ['directly related', 'strong relationship', 'dependency', 'prerequisite', 'blocking']
    if any(indicator in line_lower for indicator in high_indicators):
        return 'high'
    
    # Medium confidence indicators
    medium_indicators = ['related', 'similar', 'associated', 'part of', 'related to']
    if any(indicator in line_lower for indicator in medium_indicators):
        return 'medium'
    
    # Default to low confidence
    return 'low'

def determine_relationship_type(line, related_item, selected_work_item):
    """Determine relationship type based on context analysis."""
    line_lower = line.lower()
    
    if 'dependency' in line_lower or 'prerequisite' in line_lower:
        return 'dependency'
    elif 'feature' in line_lower or 'enhancement' in line_lower:
        return 'feature'
    elif 'bug' in line_lower or 'fix' in line_lower:
        return 'bug'
    elif 'blocking' in line_lower:
        return 'blocking'
    else:
        return 'related'

def extract_reasoning(line, related_item, selected_work_item):
    """Extract reasoning from the LLM response line."""
    # This is a simplified extraction - in production, you'd want more sophisticated parsing
    return f"AI identified relationship based on analysis of work item content and context. {line[:200]}..."

def generate_analysis_insights(related_work_items, selected_work_item, relationship_patterns=None, risk_assessment=None, recommendations=None):
    """Generate analysis insights based on related work items and extracted LLM sections."""
    
    # Count confidence levels based on numeric values
    confidence_counts = {'high': 0, 'medium': 0, 'low': 0}
    for item in related_work_items:
        confidence = item.get('confidence', 0)
        if confidence >= 0.8:
            confidence_counts['high'] += 1
        elif confidence >= 0.5:
            confidence_counts['medium'] += 1
        else:
            confidence_counts['low'] += 1
    
    # Generate risks from extracted risk assessment or fallback to generated ones
    risks = []
    if risk_assessment:
        # Process extracted risk assessment content
        for line in risk_assessment:
            if line.strip() and not line.startswith('#'):
                # Look for risk indicators in the line
                if any(keyword in line.lower() for keyword in ['risk', 'blocking', 'conflict', 'dependency', 'issue', 'problem']):
                    # Extract title and description from the line
                    title = 'AI Identified Risk'
                    description = line.strip()
                    
                    # Try to extract a more specific title
                    if ':' in line:
                        parts = line.split(':', 1)
                        if len(parts) == 2:
                            potential_title = parts[0].strip()
                            if len(potential_title) < 50:  # Reasonable title length
                                title = potential_title
                                description = parts[1].strip()
                    
                    # Determine severity based on keywords
                    severity = 'low'
                    if any(word in line.lower() for word in ['high', 'critical', 'urgent', 'blocking', 'failing']):
                        severity = 'high'
                    elif any(word in line.lower() for word in ['medium', 'significant', 'important']):
                        severity = 'medium'
                    
                    risks.append({
                        'title': title,
                        'description': description,
                        'severity': severity
                    })
    else:
        # Fallback to generated risks
        if confidence_counts.get('low', 0) > 2:
            risks.append({
                'title': 'Multiple Low Confidence Items',
                'description': f"Found {confidence_counts['low']} items with low confidence relationships. Review these carefully.",
                'severity': 'medium'
            })
    
    # Generate opportunities
    opportunities = []
    
    # Add opportunities based on confidence levels
    if confidence_counts.get('high', 0) > 3:
        opportunities.append({
            'title': 'Strong Relationship Network',
            'description': f"Found {confidence_counts['high']} high-confidence relationships. Consider coordinating these work items.",
            'type': 'optimization'
        })
    
    # Add opportunities based on relationship patterns
    if relationship_patterns:
        for line in relationship_patterns:
            if line.strip() and not line.startswith('#'):
                # Look for opportunity indicators
                if any(keyword in line.lower() for keyword in ['opportunity', 'optimization', 'enhancement', 'improvement', 'coordinate', 'leverage', 'shared']):
                    opportunities.append({
                        'title': 'Pattern-Based Opportunity',
                        'description': line.strip(),
                        'type': 'enhancement'
                    })
    
    # Add opportunities based on cross-team dependencies
    if any('cross-team' in line.lower() or 'team' in line.lower() for line in relationship_patterns):
        opportunities.append({
            'title': 'Cross-Team Coordination',
            'description': "Multiple teams are involved in related work items. Consider establishing cross-team coordination.",
            'type': 'coordination'
        })
    
    # Generate recommendations from extracted content or fallback to generated ones
    recommendations_list = []
    if recommendations:
        # Process extracted recommendations content
        for line in recommendations:
            if line.strip() and not line.startswith('#'):
                # Look for recommendation indicators in the line
                if any(keyword in line.lower() for keyword in ['recommend', 'suggest', 'action', 'consider', 'should', 'must', 'coordinate', 'review', 'audit']):
                    # Extract title and description from the line
                    title = 'AI Recommendation'
                    description = line.strip()
                    
                    # Try to extract a more specific title
                    if ':' in line:
                        parts = line.split(':', 1)
                        if len(parts) == 2:
                            potential_title = parts[0].strip()
                            if len(potential_title) < 50:  # Reasonable title length
                                title = potential_title
                                description = parts[1].strip()
                    elif line.startswith('- '):
                        # Handle bullet point format
                        title = line[2:].strip()
                        description = line[2:].strip()
                    
                    # Determine priority based on keywords
                    priority = 'medium'
                    if any(word in line.lower() for word in ['critical', 'urgent', 'immediate', 'high', 'priority']):
                        priority = 'high'
                    elif any(word in line.lower() for word in ['low', 'optional', 'consider']):
                        priority = 'low'
                    
                    recommendations_list.append({
                        'title': title,
                        'description': description,
                        'priority': priority
                    })
    else:
        # Fallback to generated recommendations
        if confidence_counts.get('high', 0) > 0:
            recommendations_list.append({
                'title': 'Prioritize High Confidence Items',
                'description': "Focus on work items with high confidence relationships first.",
                'priority': 'high'
            })
    
    # Generate relationship patterns analysis
    patterns_analysis = {
        'primaryPatterns': [],
        'dependencyClusters': [],
        'crossTeamDependencies': [],
        'technicalDebtIndicators': []
    }
    
    if relationship_patterns:
        # Process extracted relationship patterns content
        for line in relationship_patterns:
            if line.strip() and not line.startswith('#'):
                line_lower = line.lower()
                if any(keyword in line_lower for keyword in ['pattern', 'common', 'frequent']):
                    patterns_analysis['primaryPatterns'].append(line.strip())
                elif any(keyword in line_lower for keyword in ['cluster', 'group', 'dependency']):
                    patterns_analysis['dependencyClusters'].append(line.strip())
                elif any(keyword in line_lower for keyword in ['cross-team', 'team', 'coordination']):
                    patterns_analysis['crossTeamDependencies'].append(line.strip())
                elif any(keyword in line_lower for keyword in ['debt', 'refactor', 'technical']):
                    patterns_analysis['technicalDebtIndicators'].append(line.strip())
    
    return {
        'risks': risks,
        'opportunities': opportunities,
        'dependencies': [],
        'recommendations': recommendations_list,
        'relationshipPatterns': patterns_analysis,
        'summary': {
            'totalRelatedItems': len(related_work_items),
            'highConfidenceItems': confidence_counts.get('high', 0),
            'mediumConfidenceItems': confidence_counts.get('medium', 0),
            'lowConfidenceItems': confidence_counts.get('low', 0),
            'risksIdentified': len(risks),
            'opportunitiesFound': len(opportunities),
            'dependenciesFound': 0,
            'recommendationsGenerated': len(recommendations_list)
        }
    }

def get_comprehensive_mock_data():
    """Get comprehensive mock analysis data for demo purposes with work item 2217890 complete hierarchy."""
    return {
    "selectedWorkItem": {
        "id": 2217890,
        "title": "Move \"Asia\" to the High Coverage section on the Customize Featured Jurisdictions pop up",
        "type": "User Story",
        "state": "Resolved",
        "assignedTo": "Mahalingam, Ponraj (TR Technology)",
        "areaPath": "Your Project Name\\Practical Law DM2\\AEM",
        "iterationPath": "Your Project Name\\2025\\Q3\\2025_S18_Aug27-Sep09",
        "description": "<div><a href=\"https://trten.sharepoint.com/:w:/r/sites/intr-pl-enhancements/_layouts/15/Doc.aspx?sourcedoc=%7b4DD0957A-6E9D-401E-8045-996612C80C90%7d&amp;file=PL%20Global%20Jurisdiction%20page%20creation.docx&amp;wdOrigin=TEAMS-MAGLEV.p2p_ns.rwc&amp;action=default&amp;mobileredirect=true\">PL Global Jurisdiction page creation.docx</a>&nbsp;- See section<br> </div><div><br> </div>",
        "reason": "",
        "priority": 2,
        "severity": "Medium",
        "tags": [],
        "createdDate": "2025-08-19",
        "changedDate": "2025-09-03"
    },
    "relatedWorkItems": [
        {
            "id": 2228901,
            "title": "[Tech] PL Global: Add Knowledge Map - Map rendering adjustments",
            "type": "Task",
            "state": "Active",
            "assignedTo": "Mahalingam, Ponraj (TR Technology)",
            "areaPath": "Your Project Name\\Practical Law DM2\\AEM",
            "confidence": "high",
            "confidenceScore": 0.95,
            "relationship": "Implements",
            "reasoning": "Direct implementation work for Asia regional page functionality",
            "description": "Implement map rendering adjustments for the Asia regional page to ensure proper display of jurisdiction information and interactive features.",
            "sprint": "S19",
            "priority": 2
        },
        {
            "id": 2228902,
            "title": "[Tech] View Resource History functionality is not working",
            "type": "Bug",
            "state": "Active",
            "assignedTo": "Mahalingam, Ponraj (TR Technology)",
            "areaPath": "Your Project Name\\Practical Law DM2\\AEM",
            "confidence": "high",
            "confidenceScore": 0.9,
            "relationship": "Tests",
            "reasoning": "Critical bug that could affect Asia regional page testing",
            "description": "Fix the View Resource History functionality that is currently not working, which is essential for testing and validation of Asia regional page features.",
            "sprint": "S19",
            "priority": 2
        },
        {
            "id": 2228903,
            "title": "PL Core: \"Change / Compare Jurisdiction\" button text not visible in KM view",
            "type": "Bug",
            "state": "New",
            "assignedTo": "Mahalingam, Ponraj (TR Technology)",
            "areaPath": "Your Project Name\\Practical Law DM2\\AEM",
            "confidence": "high",
            "confidenceScore": 0.85,
            "relationship": "Related",
            "reasoning": "UI issue that affects jurisdiction display functionality",
            "description": "Fix the visibility issue with the Change/Compare Jurisdiction button text in Knowledge Map view, which is crucial for Asia region jurisdiction functionality.",
            "sprint": "S19",
            "priority": 5
        },
        {
            "id": 2228714,
            "title": "Clear filter is not working as expected for Asia jurisdictions",
            "type": "Bug",
            "state": "New",
            "assignedTo": "Mahalingam, Ponraj (TR Technology)",
            "areaPath": "Your Project Name\\Practical Law DM2\\AEM",
            "confidence": "medium",
            "confidenceScore": 0.65,
            "relationship": "Related",
            "reasoning": "Filter functionality may be related to jurisdiction customization",
            "description": "Fix the clear filter functionality for Asia jurisdictions to ensure proper filtering and search capabilities on the Asia regional page.",
            "sprint": "S19",
            "priority": 5
        },
        {
            "id": 2228904,
            "title": "Add flag for Asia on the Asia regional page and on All Jurisdictions page as well",
            "type": "Task",
            "state": "Active",
            "assignedTo": "Mahalingam, Ponraj (TR Technology)",
            "areaPath": "Your Project Name\\Practical Law DM2\\AEM",
            "confidence": "medium",
            "confidenceScore": 0.6,
            "relationship": "Implements",
            "reasoning": "Related to Asia region display but different scope",
            "description": "Add the Asia flag icon to both the Asia regional page and the All Jurisdictions page to provide visual consistency and branding.",
            "sprint": "S19",
            "priority": 2
        },
        {
            "id": 2228905,
            "title": "Update Asia region search functionality",
            "type": "Task",
            "state": "New",
            "assignedTo": "Balasubramanian, Ranjani (TR Techr)",
            "areaPath": "Your Project Name\\Practical Law DM2\\AEM",
            "confidence": "low",
            "confidenceScore": 0.4,
            "relationship": "Dependency",
            "reasoning": "May be required for proper Asia region functionality",
            "description": "Enhance search functionality specifically for Asia region content to improve discoverability and user experience.",
            "sprint": "S20",
            "priority": 3
        },
        {
            "id": 2228906,
            "title": "Create Asia region documentation",
            "type": "Task",
            "state": "New",
            "assignedTo": "Yesenia Capalbo (TR Product)",
            "areaPath": "Your Project Name\\Practical Law DM2\\AEM",
            "confidence": "low",
            "confidenceScore": 0.35,
            "relationship": "Support",
            "reasoning": "Documentation work that may be related to Asia region launch",
            "description": "Create comprehensive documentation for Asia region features, including user guides and technical specifications.",
            "sprint": "S20",
            "priority": 4
        },
        {
            "id": 2228907,
            "title": "Asia region accessibility compliance review",
            "type": "Task",
            "state": "New",
            "assignedTo": "Anaparthi, Sumanjali (TR Product)",
            "areaPath": "Your Project Name\\Practical Law DM2\\AEM",
            "confidence": "low",
            "confidenceScore": 0.3,
            "relationship": "Quality",
            "reasoning": "Accessibility review that may be needed for Asia region features",
            "description": "Conduct accessibility compliance review for Asia region features to ensure WCAG 2.1 AA compliance and inclusive design.",
            "sprint": "S20",
            "priority": 4
        }
    ],
    "analysisInsights": {
        "dependencies": [
            {
                "description": "Ponraj has multiple work items across S17, S18, and S19 requiring coordination",
                "impact": "High",
                "workItems": [
                    2228901,
                    2228902,
                    2228903
                ]
            },
            {
                "description": "Work items span multiple sprints requiring cross-sprint coordination and knowledge transfer",
                "impact": "Medium",
                "workItems": [
                    2228714,
                    2228904
                ]
            }
        ],
        "opportunities": [
            {
                "title": "Cross-Sprint Coordination",
                "description": "Found work items across S17, S18, and S19. Coordinating these tasks will improve efficiency.",
                "impact": "High",
                "workItems": [
                    2228901,
                    2228902,
                    2228903,
                    2228714,
                    2228904
                ]
            },
            {
                "title": "Knowledge Transfer",
                "description": "Ponraj has deep expertise in PL Global AEM and can mentor team members.",
                "impact": "Medium",
                "workItems": [
                    2228901,
                    2228904
                ]
            },
            {
                "title": "Bug Resolution Expertise",
                "description": "Multiple bug fixes across different areas show strong debugging skills.",
                "impact": "Medium",
                "workItems": [
                    2228902,
                    2228903,
                    2228714
                ]
            }
        ],
        "risks": [
            {
                "title": "Workload Distribution",
                "description": "Having multiple work items across multiple sprints may create bottlenecks.",
                "impact": "High",
                "severity": "high",
                "mitigation": "Consider redistributing some work items or providing additional support."
            },
            {
                "title": "Context Switching",
                "description": "Work items across different sprints may cause frequent context switching.",
                "impact": "Medium",
                "severity": "medium",
                "mitigation": "Group related work items together and minimize context switching."
            },
            {
                "title": "Low Confidence Dependencies",
                "description": "3 work items have low confidence relationships that may not be properly validated.",
                "impact": "Medium",
                "severity": "medium",
                "mitigation": "Review low confidence items carefully before proceeding with implementation."
            }
        ],
        "recommendations": [
            {
                "title": "Prioritize High Confidence Items",
                "description": "Focus on the 3 high confidence work items first to ensure core functionality is delivered.",
                "priority": "high",
                "workItems": [2228901, 2228902, 2228903]
            },
            {
                "title": "Coordinate with Asia Region Team",
                "description": "Schedule regular sync meetings with the Asia region development team to ensure alignment.",
                "priority": "high",
                "workItems": [2228904, 2228905]
            },
            {
                "title": "Review Low Confidence Items",
                "description": "Conduct detailed analysis of the 3 low confidence items to validate their relationship to the main work item.",
                "priority": "medium",
                "workItems": [2228905, 2228906, 2228907]
            },
            {
                "title": "Implement Cross-Sprint Coordination",
                "description": "Establish clear communication channels between S19 and S20 teams for seamless handoffs.",
                "priority": "medium",
                "workItems": [2228901, 2228902, 2228903, 2228904]
            },
            {
                "title": "Documentation and Testing Strategy",
                "description": "Ensure comprehensive documentation and testing coverage for Asia region features.",
                "priority": "low",
                "workItems": [2228906, 2228907]
            }
        ]
    },
    "confidenceScoreChart": {
        "overallConfidence": 0.65,
        "confidenceBreakdown": {
            "high": 3,
            "medium": 2,
            "low": 3
        },
        "trendData": [
            {
                "date": "2025-08-13",
                "confidence": 0.6,
                "sprint": "S17"
            },
            {
                "date": "2025-08-20",
                "confidence": 0.65,
                "sprint": "S17"
            },
            {
                "date": "2025-08-27",
                "confidence": 0.7,
                "sprint": "S18"
            },
            {
                "date": "2025-09-03",
                "confidence": 0.75,
                "sprint": "S18"
            },
            {
                "date": "2025-09-10",
                "confidence": 0.8,
                "sprint": "S19"
            },
            {
                "date": "2025-09-12",
                "confidence": 0.85,
                "sprint": "S19"
            }
        ]
    },
    "hierarchy": [
        {
            "id": 2099870,
            "title": "PL Global AEM: Asia Region Launch Support (Q2 2025)",
            "type": "Epic",
            "state": "New",
            "assignedTo": "Yesenia Capalbo (TR Product)",
            "areaPath": "Your Project Name\\Practical Law DM2\\AEM",
            "iterationPath": "Your Project Name\\2025\\Q4\\2025_S24_Nov19-Dec02",
            "description": "Support the content launch by creating a new Asia Regional Page, Consultation Board page, updating Meet the team pages, implementing Search faceting, and setting up Asia Product Coding in ACT.",
            "isSelected": False
        },
        {
            "id": 2104043,
            "title": "Complete Asia Regional Page",
            "type": "Feature",
            "state": "New",
            "assignedTo": "Balasubramanian, Ranjani (TR Techr)",
            "areaPath": "Your Project Name\\Practical Law DM2\\AEM",
            "iterationPath": "Your Project Name\\2025\\Q3\\2025_S16_Jul30-Aug12",
            "description": "Model as much as possible after the Middle East Regional Page. Need some dev work to complete the Asia Regional Page developed by Jim's team.",
            "isSelected": False
        },
        {
            "id": 2217890,
            "title": "Move \"Asia\" to the High Coverage section on the Customize Featured Jurisdictions pop up",
            "type": "User Story",
            "state": "Resolved",
            "assignedTo": "Mahalingam, Ponraj (TR Technology)",
            "areaPath": "Your Project Name\\Practical Law DM2\\AEM",
            "iterationPath": "Your Project Name\\2025\\Q3\\2025_S18_Aug27-Sep09",
            "description": "Update the featured jurisdictions customization to highlight Asia region",
            "isSelected": True
        }
    ],
    "costInfo": {
        "cost": 0.5,
        "tokens": 4000,
        "model": "gpt-4",
        "timestamp": "2025-09-12T18:46:00.139795"
    },
    "metadata": {
        "analysisDate": "2025-09-12T18:46:00.139795",
        "model": "gpt-4",
        "version": "1.8.0",
        "totalWorkItemsAnalyzed": 5,
        "dependenciesFound": 2,
        "recommendationsGenerated": 3,
        "developer": "Mahalingam, Ponraj (TR Technology)",
        "iterationsAnalyzed": 3,
        "sprintBreakdown": {
            "S17": 0,
            "S18": 0,
            "S19": 5
        },
        "dataSource": "Work Item 2217890 with complete hierarchy from Azure DevOps"
    }
}
def get_mock_analysis_data(work_item_id):
    """Get mock analysis data for demo purposes."""
    return {
        'selectedWorkItem': {
            'id': work_item_id,
            'title': 'Q2 2025 - UX for binary content - Update Basic Tab for Delivery dialog for PLUS',
            'type': 'User Story',
            'state': 'New',
            'assignedTo': 'Adadurau, Dzmitry',
            'areaPath': 'Your Project Name\\Practical Law DM2\\AEM',
            'iterationPath': 'Your Project Name\\2025\\Q3\\2025_S19_Sep10-Sep23',
            'description': 'Update the Basic Tab for Delivery dialog to improve UX for binary content handling in PLUS functionality.',
            'reason': 'Implementation started'
        },
        'hierarchy': [
            {
                'id': 2099870,
                'title': 'PL Global AEM: Asia Region Launch Support (Q2 2025)',
                'type': 'Epic',
                'state': 'New',
                'assignedTo': 'Yesenia Capalbo (TR Product)',
                'areaPath': 'Your Project Name\\Practical Law DM2\\AEM',
                'iterationPath': 'Your Project Name\\2025\\Q4\\2025_S24_Nov19-Dec02',
                'description': 'Support the content launch by creating a new Asia Regional Page, Consultation Board page, updating Meet the team pages, implementing Search faceting, and setting up Asia Product Coding in ACT.'
            },
            {
                'id': 2104043,
                'title': 'Complete Asia Regional Page',
                'type': 'Feature',
                'state': 'New',
                'assignedTo': 'Balasubramanian, Ranjani (TR Techr)',
                'areaPath': 'Your Project Name\\Practical Law DM2\\AEM',
                'iterationPath': 'Your Project Name\\2025\\Q3\\2025_S16_Jul30-Aug12',
                'description': 'Model as much as possible after the Middle East Regional Page. Need some dev work to complete the Asia Regional Page developed by Jim\'s team.'
            },
            {
                'id': work_item_id,
                'title': 'Move "Asia" to the High Coverage section on the Customize Featured Jurisdictions pop up',
                'type': 'User Story',
                'state': 'Resolved',
                'assignedTo': 'Mahalingam, Ponraj (TR Technology)',
                'areaPath': 'Your Project Name\\Practical Law DM2\\AEM',
                'iterationPath': 'Your Project Name\\2025\\Q3\\2025_S18_Aug27-Sep09',
                'description': 'Update the featured jurisdictions customization to highlight Asia region'
            }
        ],
        'relatedWorkItems': [
            # HIGH CONFIDENCE RELATIONSHIPS (3 items)
            {
                'id': 2213654,
                'title': '508: [PL AU] [Create Alert] [4.1.2]: Menu in the Alerts Contacts dialog lacks aria-label/aria-labelledby attributes.',
                'type': 'Bug',
                'state': 'Closed',
                'assignedTo': 'Anaparthi, Sumanjali (TR Product)',
                'areaPath': 'Your Project Name\\Practical Law - Accessibility',
                'iterationPath': 'Your Project Name\\2025\\Q3\\2025_S16_Jul30-Aug12',
                'confidence': 'high',
                'relationshipType': 'Technical Dependencies - Same Component/Feature Group',
                'description': 'This bug involves missing ARIA attributes on a menu component within Practical Law, which is directly related to the carousel attributes issue. Both are accessibility bugs dealing with improper or missing attributes on UI components.',
                'reasoning': 'Same area path: Your Project Name\\Practical Law - Accessibility, involvement of ARIA/accessibility attributes, 508 compliance standards (4.1.2 section), and tags including a11y-css.',
                'lastUpdated': 'Recently'
            },
            {
                'id': 2172541,
                'title': '508: [PL Connect][Jurisdiction][4.1.2]: Checkbox\'s name is inaccurate, "i" Popover and its triggering control with inaccurate role and attributes',
                'type': 'Bug',
                'state': 'Closed',
                'assignedTo': 'Anaparthi, Sumanjali (TR Product)',
                'areaPath': 'Your Project Name\\Practical Law - Accessibility',
                'iterationPath': 'Your Project Name\\2025\\Q3\\2025_S16_Jul30-Aug12',
                'confidence': 'high',
                'relationshipType': 'Technical Dependencies - Same Component/Feature Group',
                'description': 'Another Practical Law accessibility bug dealing with incorrect attributes and roles on UI controls. The pattern of attributes being "inaccurate" or "improper" is consistent.',
                'reasoning': 'Same area path: Your Project Name\\Practical Law - Accessibility, similar issue pattern, same 508 compliance section (4.1.2), assignment to the same general team structure, and tags including A11Y-2025, a11y-css, Estimate-M.',
                'lastUpdated': 'Recently'
            },
            {
                'id': 2148386,
                'title': '[PL AU] List markup solution is not applied',
                'type': 'Bug',
                'state': 'Closed',
                'assignedTo': 'Anaparthi, Sumanjali (TR Product)',
                'areaPath': 'Your Project Name\\Practical Law - Accessibility',
                'iterationPath': 'Your Project Name\\2025\\Q3\\2025_S16_Jul30-Aug12',
                'confidence': 'high',
                'relationshipType': 'Technical Dependencies - Same Component/Feature Group',
                'description': 'Another accessibility-related bug in the Practical Law area that deals with markup implementation issues.',
                'reasoning': 'Same area path and team assignment, accessibility focus, and similar technical implementation concerns.',
                'lastUpdated': 'Recently'
            },
            # MEDIUM CONFIDENCE RELATIONSHIPS (3 items)
            {
                'id': 2174716,
                'title': '508: [PL What\'s Market][Result list Public M&A][1.4.12]: Selected Menu item in the \'Format\' combo box is truncated when text spacing is applied in \'Download this document\' page.',
                'type': 'Bug',
                'state': 'New',
                'assignedTo': 'Anaparthi, Sumanjali (TR Product)',
                'areaPath': 'Your Project Name\\Practical Law - Accessibility',
                'iterationPath': 'Your Project Name\\2025\\Q3\\2025_S16_Jul30-Aug12',
                'confidence': 'medium',
                'relationshipType': 'Business Logic Relationships - Related Feature Area',
                'description': 'This is a Practical Law accessibility bug dealing with UI component behavior when accessibility features (text spacing) are applied.',
                'reasoning': 'Same area path: Your Project Name\\Practical Law - Accessibility, related to UI component behavior under accessibility conditions, and tags: A11Y-2025, Non-2025 Scope, wcag 2.1.',
                'lastUpdated': 'Recently'
            },
            {
                'id': 2225022,
                'title': '508: [Westlaw UK][Homepage/Cases/Books][4.1.2]: Missing ARIA role and attributes on infinite scroll/feed component',
                'type': 'Bug',
                'state': 'New',
                'assignedTo': 'Anaparthi, Sumanjali (TR Product)',
                'areaPath': 'Your Project Name\\Westlaw UK - Accessibility',
                'iterationPath': 'Your Project Name\\2025\\Q3\\2025_S16_Jul30-Aug12',
                'confidence': 'medium',
                'relationshipType': 'Technical Dependencies - Similar Technical Issue',
                'description': 'This bug involves missing ARIA attributes on a dynamic content component (infinite scroll), which is technically similar to carousel attribute issues.',
                'reasoning': 'Both deal with ARIA/accessibility attributes, both involve dynamic UI components (carousel vs. infinite scroll), same 508 compliance section (4.1.2), and UK product focus (PL UK vs. Westlaw UK).',
                'lastUpdated': 'Recently'
            },
            {
                'id': 2188020,
                'title': '508: [Taxnet Pro][Experts][4.1.2]: Aria attributes are not defined properly for the folder button under header navigation.',
                'type': 'Bug',
                'state': 'Resolved',
                'assignedTo': 'Anaparthi, Sumanjali (TR Product)',
                'areaPath': 'Your Project Name\\Taxnet Pro - Accessibility',
                'iterationPath': 'Your Project Name\\2025\\Q3\\2025_S16_Jul30-Aug12',
                'confidence': 'medium',
                'relationshipType': 'Technical Dependencies - Similar Technical Pattern',
                'description': 'Another case of ARIA attributes not being properly defined, showing a pattern of accessibility attribute issues across the platform.',
                'reasoning': 'Both deal with ARIA/accessibility attributes, same 508 compliance section (4.1.2), and similar technical implementation patterns.',
                'lastUpdated': 'Recently'
            },
            # LOW CONFIDENCE RELATIONSHIPS (2 items)
            {
                'id': 2174701,
                'title': '508: [PL What\'s Market][Result list Public M&A][1.4.12]: Selected Menu item in the \'Format\' combo box is truncated when text spacing is applied.',
                'type': 'Bug',
                'state': 'New',
                'assignedTo': 'Anaparthi, Sumanjali (TR Product)',
                'areaPath': 'Your Project Name\\Practical Law - Accessibility',
                'iterationPath': 'Your Project Name\\2025\\Q3\\2025_S16_Jul30-Aug12',
                'confidence': 'low',
                'relationshipType': 'Business Logic Relationships - Same Product Area',
                'description': 'Another Practical Law accessibility issue, though focused on text spacing rather than attributes.',
                'reasoning': 'Same area path but different technical focus, different WCAG section (1.4.12 vs. implied 4.1.2).',
                'lastUpdated': 'Recently'
            },
            {
                'id': 2203814,
                'title': '508: [Westlaw UK][Results Page][4.1.2]: \'Foldered\', \'Viewed\', and \'Annotated\' buttons have unnecessary attributes',
                'type': 'Bug',
                'state': 'New',
                'assignedTo': 'Anaparthi, Sumanjali (TR Product)',
                'areaPath': 'Your Project Name\\Westlaw UK - Accessibility',
                'iterationPath': 'Your Project Name\\2025\\Q3\\2025_S16_Jul30-Aug12',
                'confidence': 'low',
                'relationshipType': 'Technical Dependencies - Similar Issue Pattern',
                'description': 'This involves unnecessary attributes (opposite of missing attributes), showing attribute management issues.',
                'reasoning': 'UK product focus, attribute-related issue, same 508 section (4.1.2).',
                'lastUpdated': 'Recently'
            }
        ],
        'analysisInsights': {
            'risks': [
                {
                    'title': 'Multiple Low Confidence Items',
                    'description': 'Found 2 items with low confidence relationships. Review these carefully.',
                    'severity': 'medium'
                },
                {
                    'title': 'Shared Component Library Risk',
                    'description': 'If the carousel component is shared across multiple products, improper fixes could affect other implementations.',
                    'severity': 'high'
                },
                {
                    'title': 'Accessibility Compliance Risk',
                    'description': 'A priority 5 bug could block accessibility certification if not addressed properly.',
                    'severity': 'medium'
                }
            ],
            'opportunities': [
                {
                    'title': 'Strong Relationship Network',
                    'description': 'Found 3 high-confidence relationships. Consider coordinating these work items.',
                    'type': 'optimization'
                },
                {
                    'title': 'Cross-Product Learning',
                    'description': 'Leverage solutions from resolved Taxnet Pro bugs (2211844, 2188020) for similar accessibility issues.',
                    'type': 'enhancement'
                }
            ],
            'dependencies': [],
            'recommendations': [
                {
                    'title': 'Review Closed Related Bugs',
                    'description': 'Examine specific bug implementations (2213654, 2172541, 2148386) for patterns and solutions.',
                    'priority': 'high'
                },
                {
                    'title': 'Coordinate with Accessibility Team',
                    'description': 'Ensure fixes align with platform-wide accessibility standards given 4.1.2 violations.',
                    'priority': 'high'
                },
                {
                    'title': 'Component Audit',
                    'description': 'Check if the carousel is a shared component to understand impact scope.',
                    'priority': 'medium'
                },
                {
                    'title': 'Batch Accessibility Fixes',
                    'description': 'Group with other open PL accessibility bugs for efficient resolution.',
                    'priority': 'medium'
                },
                {
                    'title': 'Testing Strategy',
                    'description': 'Ensure automated accessibility testing covers carousel components.',
                    'priority': 'high'
                }
            ],
            'relationshipPatterns': {
                'primaryPatterns': [
                    'Accessibility Attribute Issues: Clear pattern of ARIA and other accessibility attributes being improperly implemented across multiple products.',
                    '508 Compliance Section 4.1.2: Multiple bugs referencing the same WCAG criterion.',
                    'UI Component Accessibility: Dynamic components consistently having attribute issues.'
                ],
                'dependencyClusters': [
                    'Practical Law Accessibility Cluster: Items 2213654, 2172541, 2148386 forming a cluster of related PL accessibility issues.',
                    'Attribute Implementation Cluster: Items dealing with missing, improper, or unnecessary attributes.'
                ],
                'crossTeamDependencies': [
                    'Cross-team coordination needed across products (PL UK, PL AU, Westlaw UK, Taxnet Pro) for accessibility standards.'
                ],
                'technicalDebtIndicators': [
                    'Attribute-related accessibility bugs suggests technical debt in the UI framework or component library implementation.'
                ]
            },
            'summary': {
                'totalRelatedItems': 8,
                'highConfidenceItems': 3,
                'mediumConfidenceItems': 3,
                'lowConfidenceItems': 2,
                'risksIdentified': 3,
                'opportunitiesFound': 2,
                'dependenciesFound': 0,
                'recommendationsGenerated': 5
            }
        },
        'costInfo': {
            'cost': 0.0234,
            'tokens': 1250,
            'model': 'gpt-4',
            'timestamp': datetime.now().isoformat()
        }
    }

def generate_mock_llm_response(work_item, all_work_items):
    """Generate a mock LLM response for development/testing."""
    return f"""
    ANALYSIS RESULTS FOR WORK ITEM #{work_item.id}
    
    The selected work item "{work_item.fields.get('System.Title', 'No Title')}" has several related work items:
    
    ## HIGH CONFIDENCE RELATIONSHIPS
    - **ID:** 2213654
    - **ID:** 2172541
    - **ID:** 2148386
    
    ## MEDIUM CONFIDENCE RELATIONSHIPS
    - **ID:** 2174716
    - **ID:** 2225022
    - **ID:** 2188020
    
    ## LOW CONFIDENCE RELATIONSHIPS
    - **ID:** 2174701
    - **ID:** 2203814
    
    ## RELATIONSHIP PATTERNS ANALYSIS
    ### Primary Patterns
    - Accessibility Attribute Issues: Clear pattern of ARIA and other accessibility attributes being improperly implemented across multiple products
    - 508 Compliance Section 4.1.2: Multiple bugs referencing the same WCAG criterion
    - UI Component Accessibility: Dynamic components consistently having attribute issues
    
    ### Dependency Clusters
    - Practical Law Accessibility Cluster: Items 2213654, 2172541, 2148386 forming a cluster of related PL accessibility issues
    - Attribute Implementation Cluster: Items dealing with missing, improper, or unnecessary attributes
    
    ### Cross-Team Dependencies
    - Cross-team coordination needed across products (PL UK, PL AU, Westlaw UK, Taxnet Pro) for accessibility standards
    
    ### Technical Debt Indicators
    - Attribute-related accessibility bugs suggests technical debt in the UI framework or component library implementation
    
    ## RISK ASSESSMENT
    ### High-Risk Dependencies
    - Shared Component Library Risk: If the carousel component is shared across multiple products, improper fixes could affect other implementations
    - Accessibility Compliance Risk: A priority 5 bug could block accessibility certification if not addressed properly
    
    ### Blocking Issues
    - Pattern of similar issues suggests systemic problems that may complicate the fix
    
    ### Resource Conflicts
    - Bugs in the same area path may create resource contention for specialized accessibility expertise
    
    ## RECOMMENDATIONS
    ### Immediate Actions
    - Review Closed Related Bugs: Examine specific bug implementations (2213654, 2172541, 2148386) for patterns and solutions
    - Coordinate with Accessibility Team: Ensure fixes align with platform-wide accessibility standards given 4.1.2 violations
    - Component Audit: Check if the carousel is a shared component
    
    ### Planning Considerations
    - Batch Accessibility Fixes: Group with other open PL accessibility bugs
    - Cross-Product Learning: Leverage solutions from resolved Taxnet Pro bugs (2211844, 2188020)
    - Testing Strategy: Ensure automated accessibility testing covers carousel components
    
    ### Risk Mitigation
    - Documentation: Document proper attribute placement patterns for carousels
    - Code Review: Implement accessibility-focused code review for UI component changes
    - Training: Team training on WCAG 4.1.2 requirements
    
    ### Optimization Opportunities
    - Shared Solution Patterns: Create reusable patterns for ARIA attribute implementation
    - Automated Validation: Implement build-time validation for proper attribute placement
    """

if __name__ == '__main__':
    try:
        initialize_clients()
        app.run(debug=True, host='0.0.0.0', port=5001)
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        sys.exit(1)
