#!/usr/bin/env python3
"""
Azure DevOps AI Studio - Enhanced Modern UI Backend
Complete REST API to replace all Tkinter GUI functionality with React frontend
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

# Import semantic similarity module
try:
    from SemanticSimilarity.backend_api import register_semantic_similarity_routes
    SEMANTIC_SIMILARITY_AVAILABLE = True
except ImportError as e:
    print(f"Semantic similarity module not available: {e}")
    SEMANTIC_SIMILARITY_AVAILABLE = False

# Set up logging with UTF-8 encoding to handle Unicode characters
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
# Configure the root logger to use UTF-8 encoding
for handler in logging.root.handlers:
    if hasattr(handler, 'stream') and hasattr(handler.stream, 'reconfigure'):
        handler.stream.reconfigure(encoding='utf-8')
logger = logging.getLogger(__name__)

app = Flask(__name__, 
            static_folder='../modern_ui/build',
            static_url_path='')

# Configure CORS to allow requests from the React frontend
CORS(app, 
     origins=['http://localhost:3000', 'http://127.0.0.1:3000'],
     allow_headers=['Content-Type', 'Authorization'],
     methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])

# Disable Werkzeug HTTP request logs to reduce noise
logging.getLogger('werkzeug').setLevel(logging.WARNING)

# Global variables for client instances
ado_client = None
openarena_client = None

# Session configuration to store current settings
session_config = {
    'azure_devops': {
        'org_url': '',
        'pat': '',
        'project': '',
        'connected': False
    },
    'openarena': {
        'esso_token': '',
        'websocket_url': '',
        'workflow_id': '',
        'connected': False,
        'selected_model': 'claude-4.1-opus'  # Default to Claude 4.1 Opus
    },
    'current_team': {
        'id': '',
        'name': '',
        'area_paths': []
    },
    'filters': {
        'work_item_types': [],
        'states': [],
        'assigned_to': [],
        'area_paths': [],
        'iterations': []
    },
    'auto_selection': {
        'enabled': False,
        'user_priority': 'balanced',  # options: 'speed', 'cost', 'quality', 'coding', 'balanced'
        'last_auto_selected': None,
        'fallback_model': 'claude-4.1-opus'
    }
}

def load_config_from_file():
    """Load Azure DevOps configuration from config file."""
    try:
        config_file = os.path.join(os.path.dirname(__file__), '..', 'config', 'ado_settings.txt')
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if '=' in line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        if key == 'organization_url':
                            session_config['azure_devops']['org_url'] = value
                        elif key == 'pat':
                            session_config['azure_devops']['pat'] = value
                        elif key == 'project':
                            session_config['azure_devops']['project'] = value
            logger.info("Configuration loaded from ado_settings.txt")
        else:
            logger.warning(f"Config file not found: {config_file}")
    except Exception as e:
        logger.error(f"Error loading config from file: {e}")

def initialize_clients():
    """Initialize Azure DevOps and OpenArena clients."""
    global ado_client, openarena_client
    
    try:
        # Load environment variables first
        from src.openarena.config.env_config import set_environment_variables
        set_environment_variables()
        
        # Load Azure DevOps configuration from config file if session is empty
        if not session_config['azure_devops']['org_url']:
            load_config_from_file()
        
        # Get Azure DevOps configuration from environment or session
        org_url = session_config['azure_devops']['org_url'] or os.getenv('AZURE_DEVOPS_ORG_URL')
        pat = session_config['azure_devops']['pat'] or os.getenv('AZURE_DEVOPS_PAT')
        project = session_config['azure_devops']['project'] or os.getenv('AZURE_DEVOPS_PROJECT')
        
        # Initialize default model workflow ID
        try:
            from src.openarena.config.env_config import OPENARENA_CLAUDE41OPUS_WORKFLOW_ID
            if not session_config['openarena']['workflow_id']:
                session_config['openarena']['workflow_id'] = OPENARENA_CLAUDE41OPUS_WORKFLOW_ID
                logger.info(f"Set default workflow ID: {OPENARENA_CLAUDE41OPUS_WORKFLOW_ID}")
        except ImportError:
            logger.warning("Could not load default model workflow ID")
        
        if org_url and pat:
            # Initialize Azure DevOps client with real data
            ado_client = AzureDevOpsClient(org_url, pat)
            session_config['azure_devops']['connected'] = True
            session_config['azure_devops']['org_url'] = org_url
            session_config['azure_devops']['pat'] = pat
            session_config['azure_devops']['project'] = project
            logger.info(f"Azure DevOps client initialized successfully for {org_url}")
            logger.info(f"Project configured: {project}")
        else:
            logger.warning("Azure DevOps credentials not found")
            session_config['azure_devops']['connected'] = False
        
        # Initialize OpenArena client
        openarena_client = OpenArenaWebSocketClient()
        session_config['openarena']['connected'] = True
        logger.info("OpenArena client initialized successfully")
        
        # Store clients in app config for semantic similarity routes
        app.config['ado_client'] = ado_client
        app.config['openarena_client'] = openarena_client
        
        # Register semantic similarity routes if available
        if SEMANTIC_SIMILARITY_AVAILABLE:
            try:
                register_semantic_similarity_routes(app, ado_client, openarena_client)
                logger.info("Semantic similarity routes registered successfully")
            except Exception as e:
                logger.warning(f"Failed to register semantic similarity routes: {e}")
        else:
            logger.info("Semantic similarity module not available")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize clients: {e}")
        session_config['azure_devops']['connected'] = False
        session_config['openarena']['connected'] = False
        return False

# ===== FRONTEND ROUTES =====

@app.route('/')
def serve_react_app():
    """Serve the React application."""
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_react_routes(path):
    """Serve React routes."""
    return send_from_directory(app.static_folder, 'index.html')

# ===== CONNECTION MANAGEMENT APIS =====

@app.route('/api/connection/status')
def get_connection_status():
    """Get current connection status for both Azure DevOps and OpenArena."""
    return jsonify({
        'azure_devops': {
            'connected': session_config['azure_devops']['connected'],
            'org_url': session_config['azure_devops']['org_url'],
            'project': session_config['azure_devops']['project']
        },
        'openarena': {
            'connected': session_config['openarena']['connected'],
            'selected_model': session_config['openarena']['selected_model']
        }
    })

@app.route('/api/connection/azure-devops', methods=['POST'])
def connect_azure_devops():
    """Connect to Azure DevOps with provided credentials."""
    try:
        data = request.json
        org_url = data.get('org_url')
        pat = data.get('pat')
        project = data.get('project', '')
        
        if not org_url or not pat:
            return jsonify({'error': 'Organization URL and PAT are required'}), 400
        
        # Store in session config
        session_config['azure_devops']['org_url'] = org_url
        session_config['azure_devops']['pat'] = pat
        session_config['azure_devops']['project'] = project
        
        # Test connection
        global ado_client
        ado_client = AzureDevOpsClient(org_url, pat)
        app.config['ado_client'] = ado_client
        
        # Test the connection by trying to get projects
        projects = ado_client.get_projects()
        
        session_config['azure_devops']['connected'] = True
        
        return jsonify({
            'success': True,
            'message': 'Connected to Azure DevOps successfully',
            'projects': projects
        })
        
    except Exception as e:
        logger.error(f"Error connecting to Azure DevOps: {e}")
        session_config['azure_devops']['connected'] = False
        return jsonify({'error': str(e)}), 500

@app.route('/api/connection/openarena', methods=['POST'])
def connect_openarena():
    """Connect to OpenArena with provided credentials."""
    try:
        data = request.json
        esso_token = data.get('esso_token')
        websocket_url = data.get('websocket_url')
        workflow_id = data.get('workflow_id')
        
        # Store in session config
        session_config['openarena']['esso_token'] = esso_token or ''
        session_config['openarena']['websocket_url'] = websocket_url or ''
        session_config['openarena']['workflow_id'] = workflow_id or ''
        
        # Test connection
        global openarena_client
        openarena_client = OpenArenaWebSocketClient()
        app.config['openarena_client'] = openarena_client
        
        # Test the connection
        test_result = openarena_client.test_connection()
        
        session_config['openarena']['connected'] = test_result
        
        return jsonify({
            'success': test_result,
            'message': 'OpenArena connection tested successfully' if test_result else 'OpenArena connection failed'
        })
        
    except Exception as e:
        logger.error(f"Error connecting to OpenArena: {e}")
        session_config['openarena']['connected'] = False
        return jsonify({'error': str(e)}), 500

@app.route('/api/connection/test-openarena')
def test_openarena_connection():
    """Test OpenArena connection."""
    try:
        if not openarena_client:
            return jsonify({'connected': False, 'message': 'OpenArena client not initialized'})
        
        # Test the connection
        test_result = openarena_client.test_connection()
        
        return jsonify({
            'connected': test_result,
            'message': 'Connection successful' if test_result else 'Connection failed'
        })
        
    except Exception as e:
        logger.error(f"Error testing OpenArena connection: {e}")
        return jsonify({'connected': False, 'error': str(e)})

# ===== PROJECT AND TEAM MANAGEMENT APIS =====

@app.route('/api/projects')
def get_projects():
    """Get all Azure DevOps projects."""
    try:
        if not ado_client:
            return jsonify({'error': 'Azure DevOps client not connected'}), 400
        
        projects = ado_client.get_projects()
        return jsonify(projects)
        
    except Exception as e:
        logger.error(f"Error getting projects: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/teams')
def get_teams():
    """Get all teams for a specific project."""
    try:
        if not ado_client:
            return jsonify({'error': 'Azure DevOps client not connected'}), 400
        
        # Get project from query parameter, fallback to session config
        project = request.args.get('project')
        if not project:
            project = session_config['azure_devops'].get('project')
        
        if not project:
            return jsonify({'error': 'No project specified. Please provide a project parameter or configure a default project.'}), 400
        
        logger.info(f"Getting teams for project: {project}")
        teams = ado_client.get_teams(project)
        
        # Load team verification status from mapping file
        verified_teams = set()
        try:
            import json
            import os
            mapping_file = os.path.join(os.path.dirname(__file__), '..', 'config', 'team_area_paths.json')
            if os.path.exists(mapping_file):
                with open(mapping_file, 'r', encoding='utf-8') as f:
                    mapping_data = json.load(f)
                    mappings = mapping_data.get('mappings', {})
                    for team_name, team_data in mappings.items():
                        if team_data.get('verified', False):
                            verified_teams.add(team_name)
        except Exception as e:
            logger.warning(f"Error loading team verification status: {e}")
        
        # Convert Team objects to dictionaries for JSON serialization
        teams_data = []
        if teams:
            for team in teams:
                team_name = team.name if hasattr(team, 'name') else str(team)
                is_verified = team_name in verified_teams
                team_data = {
                    'name': team_name,
                    'id': team.id if hasattr(team, 'id') else '',
                    'description': team.description if hasattr(team, 'description') else '',
                    'url': team.url if hasattr(team, 'url') else '',
                    'identity_url': team.identity_url if hasattr(team, 'identity_url') else '',
                    'verified': is_verified
                }
                teams_data.append(team_data)
        
        # Sort teams alphabetically by name
        teams_data.sort(key=lambda x: x['name'].lower())
        
        verified_count = len([t for t in teams_data if t['verified']])
        logger.info(f"Returning {len(teams_data)} teams for project: {project} ({verified_count} verified)")
        return jsonify({
            'teams': teams_data,
            'verified_count': verified_count,
            'total_count': len(teams_data)
        })
        
    except Exception as e:
        logger.error(f"Error getting teams: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects/<project_name>/teams')
def get_teams_by_project(project_name):
    """Get all teams for a specific project (RESTful endpoint)."""
    try:
        if not ado_client:
            return jsonify({'error': 'Azure DevOps client not connected'}), 400
        
        logger.info(f"Getting teams for project: {project_name}")
        teams = ado_client.get_teams(project_name)
        
        # Load team verification status from mapping file
        verified_teams = set()
        try:
            import json
            import os
            mapping_file = os.path.join(os.path.dirname(__file__), '..', 'config', 'team_area_paths.json')
            if os.path.exists(mapping_file):
                with open(mapping_file, 'r', encoding='utf-8') as f:
                    mapping_data = json.load(f)
                    mappings = mapping_data.get('mappings', {})
                    for team_name, team_data in mappings.items():
                        if team_data.get('verified', False):
                            verified_teams.add(team_name)
        except Exception as e:
            logger.warning(f"Error loading team verification status: {e}")
        
        # Convert Team objects to dictionaries for JSON serialization
        teams_data = []
        if teams:
            for team in teams:
                team_name = team.name if hasattr(team, 'name') else str(team)
                team_data = {
                    'name': team_name,
                    'id': team.id if hasattr(team, 'id') else '',
                    'description': team.description if hasattr(team, 'description') else '',
                    'url': team.url if hasattr(team, 'url') else '',
                    'identity_url': team.identity_url if hasattr(team, 'identity_url') else '',
                    'verified': team_name in verified_teams
                }
                teams_data.append(team_data)
        
        # Sort teams alphabetically by name
        teams_data.sort(key=lambda x: x['name'].lower())
        
        verified_count = len([t for t in teams_data if t['verified']])
        logger.info(f"Returning {len(teams_data)} teams for project: {project_name} ({verified_count} verified)")
        return jsonify({
            'teams': teams_data,
            'verified_count': verified_count,
            'total_count': len(teams_data)
        })
        
    except Exception as e:
        logger.error(f"Error getting teams for project {project_name}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/teams/<team_id>/area-paths')
def get_team_area_paths(team_id):
    """Get area paths for a specific team."""
    try:
        if not ado_client:
            return jsonify({'error': 'Azure DevOps client not connected'}), 400
        
        area_paths = ado_client.get_team_area_paths(team_id)
        
        # Update session config
        session_config['current_team']['id'] = team_id
        session_config['current_team']['area_paths'] = area_paths
        
        return jsonify(area_paths)
        
    except Exception as e:
        logger.error(f"Error getting team area paths: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/current-team', methods=['GET'])
def get_current_team():
    """Get the current team."""
    try:
        return jsonify(session_config['current_team'])
        
    except Exception as e:
        logger.error(f"Error getting current team: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/current-team', methods=['POST'])
def set_current_team():
    """Set the current team."""
    try:
        data = request.json
        team_id = data.get('team_id')
        team_name = data.get('team_name')
        
        session_config['current_team']['id'] = team_id
        session_config['current_team']['name'] = team_name
        
        return jsonify({'success': True, 'message': f'Current team set to {team_name}'})
        
    except Exception as e:
        logger.error(f"Error setting current team: {e}")
        return jsonify({'error': str(e)}), 500

# Auto Team Selection API Routes
@app.route('/api/user/profile', methods=['GET'])
def get_user_profile():
    """Get user profile and preferences."""
    try:
        # For now, return a default profile
        # In a real implementation, this would fetch from a database
        profile = {
            'userId': 'current_user',
            'preferences': {
                'autoSelectTeam': True,
                'defaultTeam': None,
                'teamSelectionStrategy': 'hybrid'  # 'profile', 'activity', 'hybrid'
            },
            'lastUpdated': datetime.now().isoformat()
        }
        
        return jsonify(profile)
        
    except Exception as e:
        logger.error(f"Error getting user profile: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/user/profile', methods=['PUT'])
def update_user_profile():
    """Update user profile and preferences."""
    try:
        data = request.json
        logger.info(f"Updating user profile: {data}")
        
        # In a real implementation, this would save to a database
        # For now, just return success
        return jsonify({'success': True, 'message': 'Profile updated successfully'})
        
    except Exception as e:
        logger.error(f"Error updating user profile: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/teams/workitem-counts', methods=['GET'])
def get_team_workitem_counts():
    """Get work item counts for each team for the current user."""
    try:
        if not ado_client:
            return jsonify({'error': 'Azure DevOps client not connected'}), 400
        
        project_name = request.args.get('project')
        user_name = request.args.get('user', 'current_user')
        
        if not project_name:
            return jsonify({'error': 'Project name is required'}), 400
        
        # Get all teams for the project
        teams = ado_client.get_teams(project_name)
        team_counts = []
        
        for team in teams:
            team_name = team['name']
            try:
                # Query work items for this team and user
                work_items = ado_client.query_work_items_by_team_and_user(project_name, team_name, user_name)
                count = len(work_items)
                
                team_counts.append({
                    'teamId': team['id'],
                    'teamName': team_name,
                    'workItemCount': count,
                    'lastActivity': datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.warning(f"Error getting work item count for team {team_name}: {e}")
                team_counts.append({
                    'teamId': team['id'],
                    'teamName': team_name,
                    'workItemCount': 0,
                    'lastActivity': None,
                    'error': str(e)
                })
        
        return jsonify(team_counts)
        
    except Exception as e:
        logger.error(f"Error getting team work item counts: {e}")
        return jsonify({'error': str(e)}), 500

def verify_team_active(team_data, work_item_counts):
    """Verify if a team is active based on work item counts."""
    team_id = team_data.get('id')
    for count_data in work_item_counts:
        if count_data.get('teamId') == team_id:
            return count_data.get('workItemCount', 0) > 0
    return False

def calculate_confidence_score(team_data, work_item_counts, user_preferences):
    """Calculate confidence score for team selection."""
    team_id = team_data.id if hasattr(team_data, 'id') else team_data.get('id')
    team_name = team_data.name if hasattr(team_data, 'name') else team_data.get('name', '')
    
    # Base score
    score = 0.0
    reasons = []
    
    # Work item count factor (0-20 points) - reduced since we're not counting
    work_item_count = 0
    for count_data in work_item_counts:
        if count_data.get('teamId') == team_id:
            work_item_count = count_data.get('workItemCount', 0)
            break
    
    if work_item_count > 0:
        score += min(20, work_item_count * 2)  # Cap at 20 points
        reasons.append(f"Active team with {work_item_count} work items")
    else:
        # Give some points for being a team (since we can't count work items quickly)
        score += 5
        reasons.append("Available team for selection")
    
    # Team name pattern matching (0-50 points) - increased to compensate for work item scoring
    if 'accessibility' in team_name.lower() or 'a11y' in team_name.lower():
        score += 50
        reasons.append("Accessibility-focused team")
    elif 'legal' in team_name.lower():
        score += 40
        reasons.append("Legal domain team")
    elif 'cobalt' in team_name.lower():
        score += 30
        reasons.append("Cobalt project team")
    elif 'general' in team_name.lower() or 'main' in team_name.lower():
        score += 25
        reasons.append("General/Main team")
    
    # User preference matching (0-20 points)
    default_team = user_preferences.get('defaultTeam')
    if default_team and default_team.lower() in team_name.lower():
        score += 20
        reasons.append("Matches user's default team preference")
    
    # Strategy-specific scoring (0-20 points) - increased
    strategy = user_preferences.get('teamSelectionStrategy', 'hybrid')
    if strategy == 'activity' and work_item_count > 0:
        score += 20
        reasons.append("High activity team")
    elif strategy == 'profile' and 'accessibility' in team_name.lower():
        score += 20
        reasons.append("Profile-matched team")
    elif strategy == 'hybrid':
        score += 15
        reasons.append("Balanced selection approach")
    
    return min(100, score), reasons

def get_project_default_team(project_name):
    """Get the default team for a project based on naming patterns."""
    try:
        teams = ado_client.get_teams(project_name)
        
        # Look for common default team patterns
        default_patterns = [
            'main', 'default', 'primary', 'core', 'development',
            'accessibility', 'a11y', 'legal'
        ]
        
        for team in teams:
            team_name = team.name.lower() if hasattr(team, 'name') else ''
            for pattern in default_patterns:
                if pattern in team_name:
                    return team
        
        # If no pattern matches, return the first team
        return teams[0] if teams else None
        
    except Exception as e:
        logger.error(f"Error getting default team for project {project_name}: {e}")
        return None

@app.route('/api/teams/auto-select', methods=['POST'])
def auto_select_team():
    """Automatically select the best team based on user activity and preferences."""
    try:
        if not ado_client:
            return jsonify({'error': 'Azure DevOps client not connected'}), 400
        
        data = request.json
        project_id = data.get('projectId')
        user_id = data.get('userId', 'current_user')
        
        if not project_id:
            return jsonify({'error': 'Project ID is required'}), 400
        
        logger.info(f"Auto-selecting team for project: {project_id}, user: {user_id}")
        
        # Get user preferences
        user_preferences = {'autoSelectTeam': True, 'defaultTeam': None, 'teamSelectionStrategy': 'hybrid'}
        
        # Get teams and use a faster selection approach
        teams = ado_client.get_teams(project_id)
        
        # For now, use a simple team selection based on naming patterns
        # This avoids the slow work item queries that cause timeouts
        work_item_counts = []
        for team in teams:
            work_item_counts.append({
                'teamId': team.id,
                'teamName': team.name,
                'workItemCount': 0,  # Skip actual work item counting for now
                'lastActivity': datetime.now().isoformat()
            })
        
        # Calculate confidence scores for each team
        team_scores = []
        for team in teams:
            score, reasons = calculate_confidence_score(team, work_item_counts, user_preferences)
            team_scores.append({
                'team': team,
                'score': score,
                'reasons': reasons,
                'workItemCount': next((wc['workItemCount'] for wc in work_item_counts if wc['teamId'] == team.id), 0)
            })
        
        # Sort by confidence score (highest first)
        team_scores.sort(key=lambda x: x['score'], reverse=True)
        
        if not team_scores:
            return jsonify({'error': 'No teams found for auto-selection'}), 404
        
        # Select the best team
        best_team = team_scores[0]
        selected_team = best_team['team']
        
        # Update session config
        session_config['current_team']['id'] = selected_team.id
        session_config['current_team']['name'] = selected_team.name
        
        # Prepare response
        result = {
            'success': True,
            'selectedTeam': {
                'id': selected_team.id,
                'name': selected_team.name,
                'confidence': best_team['score'] / 100.0,  # Convert to 0-1 range
                'workItemCount': best_team['workItemCount'],
                'reasons': best_team['reasons']
            },
            'alternatives': [
                {
                    'id': team['team'].id,
                    'name': team['team'].name,
                    'confidence': team['score'] / 100.0,  # Convert to 0-1 range
                    'workItemCount': team['workItemCount']
                }
                for team in team_scores[1:3]  # Top 2 alternatives
            ],
            'selectionMethod': 'auto',
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"Auto-selected team: {selected_team.name} (confidence: {best_team['score']:.1f}%)")
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in auto team selection: {e}")
        return jsonify({'error': f'Auto-selection failed: {str(e)}'}), 500

@app.route('/api/analytics/team-selection', methods=['POST'])
def track_team_selection():
    """Track team selection events for analytics."""
    try:
        data = request.json
        event_type = data.get('eventType')  # 'auto_selected', 'manual_override', 'selection_failed'
        team_id = data.get('teamId')
        team_name = data.get('teamName')
        confidence = data.get('confidence')
        reason = data.get('reason')
        
        # Log the analytics event
        logger.info(f"Analytics - Team Selection Event: {event_type}")
        logger.info(f"  Team: {team_name} (ID: {team_id})")
        logger.info(f"  Confidence: {confidence}")
        logger.info(f"  Reason: {reason}")
        
        # In a real implementation, this would send to an analytics service
        # For now, just log it
        
        return jsonify({'success': True, 'message': 'Analytics event tracked'})
        
    except Exception as e:
        logger.error(f"Error tracking team selection analytics: {e}")
        return jsonify({'error': str(e)}), 500

# ===== WORK ITEMS APIS =====

@app.route('/api/work-items')
def get_work_items():
    """Get work items with optional filtering."""
    try:
        if not ado_client:
            return jsonify({'error': 'Azure DevOps client not connected'}), 400
        
        # Get query parameters for filtering
        team = request.args.get('team', 'All')
        work_item_type = request.args.get('work_item_type', 'All')
        state = request.args.get('state', 'All')
        assigned_to = request.args.get('assigned_to', 'All')
        area_path = request.args.get('area_path', 'All')
        iteration_path = request.args.get('iteration_path', 'All')
        
        # Get the current project name from session config
        project_name = session_config['azure_devops'].get('project')
        if not project_name:
            return jsonify({'error': 'No project selected'}), 400
        
        # Load team mapping and area paths from generated file
        team_mapping = {}
        team_area_paths = {}
        try:
            import json
            import os
            mapping_file = os.path.join(os.path.dirname(__file__), '..', 'config', 'team_area_paths.json')
            if os.path.exists(mapping_file):
                with open(mapping_file, 'r', encoding='utf-8') as f:
                    mapping_data = json.load(f)
                    mappings = mapping_data.get('mappings', {})
                    # Create team mapping for verified teams only
                    for team_name, team_data in mappings.items():
                        if team_data.get('verified', False):
                            team_mapping[team_name] = team_name
                            team_area_paths[team_name] = team_data.get('area_path', '')
                logger.info(f"Loaded {len(team_mapping)} verified teams from mapping file")
            else:
                logger.warning("Team mapping file not found, using empty mapping")
        except Exception as e:
            logger.error(f"Error loading team mapping: {e}")
            team_mapping = {}
            team_area_paths = {}
        
        # Prepare parameters for query_work_items
        query_team = None
        if team != 'All':
            query_team = team_mapping.get(team, team)
        
        query_work_item_type = None
        if work_item_type != 'All':
            query_work_item_type = work_item_type
        
        query_state = None
        if state != 'All':
            query_state = state
        
        # Use enhanced filters for additional filtering
        enhanced_filters = {}
        if assigned_to != 'All':
            enhanced_filters['assigned_to'] = assigned_to
        if area_path != 'All':
            enhanced_filters['area_path'] = area_path
        if iteration_path != 'All':
            enhanced_filters['iteration_path'] = iteration_path
        
        # Query work items with filters
        work_items = ado_client.query_work_items(
            project=project_name,
            team=query_team,
            work_item_type=query_work_item_type,
            state=query_state,
            limit=50000,  # Increased limit to handle large datasets
            enhanced_filters=enhanced_filters if enhanced_filters else None
        )
        
        # Format work items for frontend
        formatted_items = []
        for item in work_items:
            formatted_items.append({
                'id': item.id,
                'title': item.fields.get('System.Title', 'No Title'),
                'type': item.fields.get('System.WorkItemType', 'Unknown'),
                'state': item.fields.get('System.State', 'Unknown'),
                'assignedTo': item.fields.get('System.AssignedTo', {}).get('displayName', 'Unassigned'),
                'areaPath': item.fields.get('System.AreaPath', ''),
                'iterationPath': item.fields.get('System.IterationPath', ''),
                'priority': item.fields.get('Microsoft.VSTS.Common.Priority', ''),
                'tags': item.fields.get('System.Tags', ''),
                'createdDate': item.fields.get('System.CreatedDate', ''),
                'changedDate': item.fields.get('System.ChangedDate', ''),
                'description': item.fields.get('System.Description', '')
            })
        
        logger.info(f"[INFO] API Response: Returning {len(formatted_items)} formatted work items")
        if formatted_items:
            logger.info(f"[INFO] Sample work item: ID={formatted_items[0]['id']}, Title='{formatted_items[0]['title'][:50]}...', AreaPath='{formatted_items[0]['areaPath']}'")
        
        return jsonify(formatted_items)
        
    except Exception as e:
        logger.error(f"Error getting work items: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/work-item/<int:work_item_id>')
def get_work_item(work_item_id):
    """Get specific work item details."""
    try:
        if not ado_client:
            return jsonify({'error': 'Azure DevOps client not connected'}), 400
        
        work_item = ado_client.get_work_item(work_item_id)
        if not work_item:
            return jsonify({'error': 'Work item not found'}), 404
        
        formatted_item = {
            'id': work_item.id,
            'title': work_item.fields.get('System.Title', 'No Title'),
            'type': work_item.fields.get('System.WorkItemType', 'Unknown'),
            'state': work_item.fields.get('System.State', 'Unknown'),
            'assignedTo': work_item.fields.get('System.AssignedTo', {}).get('displayName', 'Unassigned'),
            'areaPath': work_item.fields.get('System.AreaPath', ''),
            'iterationPath': work_item.fields.get('System.IterationPath', ''),
            'priority': work_item.fields.get('Microsoft.VSTS.Common.Priority', ''),
            'tags': work_item.fields.get('System.Tags', ''),
            'createdDate': work_item.fields.get('System.CreatedDate', ''),
            'changedDate': work_item.fields.get('System.ChangedDate', ''),
            'description': work_item.fields.get('System.Description', ''),
            'reason': work_item.fields.get('System.Reason', '')
        }
        
        return jsonify(formatted_item)
        
    except Exception as e:
        logger.error(f"Error getting work item: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/work-item/<int:work_item_id>/hierarchy')
def get_work_item_hierarchy(work_item_id):
    """Get work item hierarchy."""
    try:
        if not ado_client:
            return jsonify({'error': 'Azure DevOps client not connected'}), 400
        
        hierarchy = ado_client.get_work_item_hierarchy(work_item_id)
        
        # Format hierarchy for frontend
        formatted_hierarchy = []
        if hierarchy and isinstance(hierarchy, dict):
            hierarchy_path = hierarchy.get('hierarchy_path', [])
            for item in hierarchy_path:
                formatted_hierarchy.append({
                    'id': item.id,
                    'title': item.fields.get('System.Title', 'No Title'),
                    'type': item.fields.get('System.WorkItemType', 'Unknown'),
                    'state': item.fields.get('System.State', 'Unknown'),
                    'assignedTo': item.fields.get('System.AssignedTo', {}).get('displayName', 'Unassigned'),
                    'areaPath': item.fields.get('System.AreaPath', ''),
                    'iterationPath': item.fields.get('System.IterationPath', ''),
                    'isSelected': item.id == work_item_id
                })
        
        return jsonify(formatted_hierarchy)
        
    except Exception as e:
        logger.error(f"Error getting work item hierarchy: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/work-item/<int:work_item_id>/related-items')
def get_work_item_related_items(work_item_id):
    """Get related items for a specific work item using both direct relationships and AI analysis."""
    try:
        if not ado_client:
            return jsonify({'error': 'Azure DevOps client not connected'}), 400
        
        # Get search scope and filters from query parameters
        search_scope = request.args.get('scope', 'very-specific')  # 'very-specific', 'specific', 'generic'
        date_filter = request.args.get('dateFilter', 'last-month')
        work_item_types = request.args.get('workItemTypes', 'User Story,Task,Bug,Feature,Epic').split(',')
        selected_teams = request.args.get('selectedTeams', '')  # Comma-separated list of selected teams
        
        logger.info(f"Getting related items for work item {work_item_id} with scope: {search_scope}, date: {date_filter}, types: {work_item_types}, selected_teams: {selected_teams}")
        print(f"\n[START] STARTING RELATED ITEMS SEARCH")
        print(f"   Work Item ID: {work_item_id}")
        print(f"   Scope: {search_scope}")
        print(f"   Date Filter: {date_filter}")
        print(f"   Work Item Types: {', '.join(work_item_types)}")
        print(f"   Selected Teams: '{selected_teams}' (length: {len(selected_teams)})")
        print(f"   Selected Teams Empty: {not selected_teams}")
        print("="*60)
        
        # Get the project name from session config
        project_name = session_config['azure_devops'].get('project')
        if not project_name:
            return jsonify({'error': 'No project selected'}), 400
        
        # Strategy 1: Use intelligent search based on scope
        try:
            # Get the work item first to pass to the intelligent search method
            selected_work_item = ado_client.get_work_item(work_item_id)
            if selected_work_item:
                # Determine search scope and teams to include
                teams_to_search = []
                
                if search_scope == 'very-specific':
                    # Only search the specific team from the work item's area path
                    area_path = selected_work_item.fields.get('System.AreaPath', '')
                    if area_path:
                        path_parts = area_path.split('\\')
                        if len(path_parts) >= 2:
                            team_name = path_parts[-1]
                            teams_to_search = [team_name]
                            logger.info(f"Very specific scope: searching only team '{team_name}'")
                        else:
                            logger.warning("Could not extract team name from area path, falling back to generic search")
                            search_scope = 'generic'
                    else:
                        logger.warning("No area path found, falling back to generic search")
                        search_scope = 'generic'
                
                if search_scope == 'specific':
                    # Laser Focus: Always use all 112 verified teams
                    # Load verified teams from mapping file
                    try:
                        import json
                        import os
                        mapping_file = os.path.join(os.path.dirname(__file__), '..', 'config', 'team_area_paths.json')
                        verified_teams = []
                        if os.path.exists(mapping_file):
                            with open(mapping_file, 'r', encoding='utf-8') as f:
                                mapping_data = json.load(f)
                                mappings = mapping_data.get('mappings', {})
                                for team_name, team_data in mappings.items():
                                    if team_data.get('verified', False):
                                        verified_teams.append(team_name)
                        
                        if verified_teams:
                            teams_to_search = verified_teams
                            logger.info(f"Laser Focus: Using all {len(verified_teams)} verified teams")
                            print(f"\n[SEARCH] LASER FOCUS - Using All Verified Teams")
                            print(f"   Work Item ID: {work_item_id}")
                            print(f"   Work Item Title: {selected_work_item.fields.get('System.Title', 'No Title')}")
                            print(f"   Project: {project_name}")
                            print(f"   Verified Teams: {len(verified_teams)} teams")
                            print("="*80)
                            
                            print(f"\n[STRATEGY] LASER FOCUS - Using Optimized Method")
                            print(f"   Searching {len(teams_to_search)} teams with optimized query...")
                            
                            # Use the optimized scope-based search method
                            work_item_refs = ado_client._execute_scope_based_search(
                                project_name, 
                                selected_work_item, 
                                teams_to_search, 
                                max_results_per_team=10,
                                date_filter=date_filter,
                                work_item_types=work_item_types
                            )
                            
                            if work_item_refs:
                                # Get full work item details for the references
                                related_items = []
                                for ref in work_item_refs:
                                    try:
                                        work_item = ado_client.get_work_item(ref.id)
                                        if work_item:
                                            related_items.append(work_item)
                                    except Exception as e:
                                        logger.warning(f"Failed to get details for work item {ref.id}: {e}")
                                        continue
                                
                                logger.info(f"Found {len(related_items)} total related items across {len(teams_to_search)} teams")
                                print(f"   [SUCCESS] Found {len(related_items)} total items across all teams")
                            else:
                                related_items = []
                                logger.info(f"No related items found across {len(teams_to_search)} teams")
                                print(f"   [INFO] No related items found across all teams")
                        else:
                            logger.warning("No verified teams found, falling back to generic search")
                            search_scope = 'generic'
                    except Exception as e:
                        logger.error(f"Error loading verified teams: {e}")
                        search_scope = 'generic'
                
                if search_scope == 'balanced':
                    # Balanced Search: Use all 112 verified teams (similar to Laser Focus)
                    try:
                        # Load all verified teams from mapping file
                        import os
                        import json
                        config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'team_area_paths.json')
                        if os.path.exists(config_path):
                            with open(config_path, 'r', encoding='utf-8') as f:
                                team_mappings = json.load(f)
                                mappings = team_mappings.get('mappings', {})
                                # Get all verified teams
                                teams_to_search = [name for name, data in mappings.items() if data.get('verified', False)]
                                logger.info(f"Balanced Search: Using all {len(teams_to_search)} verified teams")
                                print(f"\n[SEARCH] BALANCED SEARCH - Using All 112 Verified Teams")
                                print(f"   Work Item ID: {work_item_id}")
                                print(f"   Work Item Title: {selected_work_item.fields.get('System.Title', 'No Title')}")
                                print(f"   Project: {project_name}")
                                print(f"   Verified Teams: {len(teams_to_search)} teams")
                                print("="*80)
                        else:
                            logger.error("Could not load team mappings for balanced search")
                            # Fallback to all teams if mapping file not found
                            all_teams = ado_client.get_teams(project_name)
                            teams_to_search = [team.name for team in all_teams]
                            logger.info(f"Balanced Search: Using fallback all {len(teams_to_search)} teams")
                            print(f"\n[SEARCH] BALANCED SEARCH - Using Fallback All Teams")
                            print(f"   Work Item ID: {work_item_id}")
                            print(f"   Work Item Title: {selected_work_item.fields.get('System.Title', 'No Title')}")
                            print(f"   Project: {project_name}")
                            print(f"   All Teams: {len(teams_to_search)} teams")
                            print("="*80)
                    except Exception as e:
                        logger.error(f"Error loading verified teams for balanced search: {e}")
                        # Fallback to all teams if error occurs
                        all_teams = ado_client.get_teams(project_name)
                        teams_to_search = [team.name for team in all_teams]
                        logger.info(f"Balanced Search: Using error fallback all {len(teams_to_search)} teams")
                        print(f"\n[SEARCH] BALANCED SEARCH - Using Error Fallback All Teams")
                        print(f"   Work Item ID: {work_item_id}")
                        print(f"   Work Item Title: {selected_work_item.fields.get('System.Title', 'No Title')}")
                        print(f"   Project: {project_name}")
                        print(f"   All Teams: {len(teams_to_search)} teams")
                        print("="*80)
                    
                    # Execute balanced search with keyword logic + 3-year batching + work item types
                    work_item_refs = []
                    if teams_to_search:
                        print(f"\n[STRATEGY] BALANCED SEARCH - Using Keyword Search with 3-Year Batching")
                        print(f"   Searching {len(teams_to_search)} teams with keyword-level search and 3-year data...")
                        
                        # Use keyword search with 3-year batching logic (not title phrase matching)
                        work_item_refs = ado_client._execute_balanced_keyword_search_with_batching(
                            project_name, 
                            selected_work_item, 
                            teams_to_search, 
                            max_results_per_team=10,
                            date_filter=date_filter,
                            work_item_types=work_item_types
                        )
                
                # Only process team-based search results if we don't already have related_items from specific search
                if work_item_refs and search_scope != 'specific':
                    logger.info(f"Found {len(work_item_refs)} work item references from team-based search")
                    
                    # Get full work item details for the references
                    work_item_client = ado_client.connection.clients.get_work_item_tracking_client()
                    related_items = []
                    
                    for item_ref in work_item_refs:
                        try:
                            full_item = work_item_client.get_work_item(item_ref.id)
                            related_items.append(full_item)
                        except Exception as item_error:
                            logger.warning(f"Failed to get full details for work item {item_ref.id}: {str(item_error)}")
                            continue
                    
                    logger.info(f"Successfully retrieved {len(related_items)} related work items using team-based search")
                elif not work_item_refs and search_scope != 'specific':
                    logger.warning("No work items found with team-based search")
                    related_items = []
                
                if search_scope == 'generic':
                    # Search all teams in the project
                    all_teams = ado_client.get_teams(project_name)
                    teams_to_search = [team.name for team in all_teams]
                    logger.info(f"Generic scope: searching all {len(teams_to_search)} teams in project")
                    
                    # Execute search based on scope with filters
                    work_item_refs = []
                    if teams_to_search:
                        work_item_refs = ado_client._execute_scope_based_search(
                            project_name, 
                            selected_work_item, 
                            teams_to_search, 
                            max_results_per_team=10,
                            date_filter=date_filter,
                            work_item_types=work_item_types
                        )
            else:
                logger.warning(f"Could not retrieve work item {work_item_id}")
                related_items = []
        except Exception as e:
            logger.warning(f"Team-based intelligent search failed: {e}")
            # Fallback to basic relationship query
            try:
                related_items = ado_client.query_related_work_items(project_name, work_item_id)
                logger.info(f"Fallback: Found {len(related_items) if related_items else 0} items using basic search")
            except Exception as fallback_e:
                logger.warning(f"Fallback search also failed: {fallback_e}")
                related_items = []
        
        # No additional area path filtering - search across all teams in the project
        logger.info(f"Sophisticated title search completed with {len(related_items)} items across all teams")
        
        # No automatic LLM analysis here - user will trigger it separately with "Analysis with LLM" button
        logger.info(f"Related items search completed. Found {len(related_items)} items using intelligent title search only.")
        logger.info("Note: OpenArena LLM analysis will only run when user clicks 'Analysis with LLM' button")
        # Format results for frontend
        formatted_items = []
        for item in related_items:
            formatted_items.append({
                'id': item.id,
                'title': item.fields.get('System.Title', 'No Title'),
                'type': item.fields.get('System.WorkItemType', 'Unknown'),
                'state': item.fields.get('System.State', 'Unknown'),
                'assignedTo': item.fields.get('System.AssignedTo', {}).get('displayName', 'Unassigned'),
                'areaPath': item.fields.get('System.AreaPath', ''),
                'iterationPath': item.fields.get('System.IterationPath', ''),
                'priority': item.fields.get('Microsoft.VSTS.Common.Priority', ''),
                'tags': item.fields.get('System.Tags', ''),
                'createdDate': item.fields.get('System.CreatedDate', ''),
                'changedDate': item.fields.get('System.ChangedDate', ''),
                'relationshipType': 'related',  # Could be enhanced with more specific types
                'confidence': 'medium'  # Could be enhanced with confidence scoring
            })
        
        logger.info(f"Returning {len(formatted_items)} related items for work item {work_item_id}")
        print(f"\n[SUCCESS] SEARCH COMPLETED")
        print(f"   Total Related Items Found: {len(formatted_items)}")
        print(f"   Search Scope: {search_scope}")
        print("="*60)
        
        return jsonify(formatted_items)
        
    except Exception as e:
        logger.error(f"Error getting related items for work item {work_item_id}: {e}")
        return jsonify({'error': str(e)}), 500

# DISABLED: Team group endpoint - not used and causes unnecessary ADO API calls
# @app.route('/api/work-item/<int:work_item_id>/team-groups', methods=['GET'])
# def get_team_groups(work_item_id):
#     """Get team group information for a work item."""
#     # This endpoint has been disabled to avoid unnecessary ADO API calls
#     # The team group logic is not used in the current implementation
#     return jsonify({'error': 'Team group endpoint disabled'}), 404

# Helper functions moved to LLM analysis endpoint where they belong

# ===== FILTER MANAGEMENT APIS =====

@app.route('/api/filters/options')
def get_filter_options():
    """Get available filter options without loading all work items."""
    try:
        if not ado_client:
            return jsonify({'error': 'Azure DevOps client not connected'}), 400
        
        # Return static filter options to avoid loading all work items
        # These are common Azure DevOps work item types and states
        work_item_types = [
            'Epic', 'Feature', 'User Story', 'Task', 'Bug', 'Test Case', 
            'Design Task', 'Code Review', 'Documentation', 'Spike'
        ]
        
        states = [
            'New', 'Active', 'Resolved', 'Closed', 'Removed', 'Done', 'To Do', 'In Progress'
        ]
        
        # For teams, we'll use a more efficient approach
        # Get teams from the project structure instead of all work items
        teams = []
        try:
            # Try to get teams from the project
            # This is a simplified approach - in a real implementation, you'd query the teams API
            teams = ['Practical Law - Accessibility', 'Practical Law - Core', 'Practical Law - UK']
        except:
            teams = ['Practical Law - Accessibility']  # Fallback
        
        return jsonify({
            'workItemTypes': work_item_types,
            'states': states,
            'assignedTo': [],  # Will be populated when work items are loaded
            'areaPaths': [],   # Will be populated when work items are loaded
            'iterationPaths': [],  # Will be populated when work items are loaded
            'teams': teams
        })
        
    except Exception as e:
        logger.error(f"Error getting filter options: {e}")
        return jsonify({'error': str(e)}), 500

# ===== LLM ANALYSIS APIS (Enhanced from existing app.py) =====

@app.route('/api/analysis/<int:work_item_id>')
def get_analysis_data(work_item_id):
    """Get LLM analysis data for a specific work item."""
    try:
        # First, try to load analysis data from GUI if available
        analysis_data = load_analysis_data_from_gui(work_item_id)
        if analysis_data and analysis_data != {}:
            logger.info(f"Loaded analysis data from GUI for work item {work_item_id}")
            return jsonify(analysis_data)
        
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
                system_prompt = analysis_prompt.create_simplified_prompt(work_item, all_work_items)
                
                # Get LLM response from OpenArena
                if openarena_client:
                    # Use the selected model workflow for analysis
                    selected_model = session_config['openarena']['selected_model']
                    workflow_id = session_config['openarena']['workflow_id']
                    
                    llm_response, cost_tracker = openarena_client.query_workflow(
                        workflow_id=workflow_id,
                        query=system_prompt,
                        is_persistence_allowed=False
                    )
                else:
                    # Fallback to mock response for development
                    llm_response = generate_mock_llm_response(main_work_item, all_work_items)
                    cost_tracker = {}
                
                # Process LLM response to extract structured data
                analysis_data = process_llm_response(llm_response, main_work_item, all_work_items, hierarchy)
                
                return jsonify(analysis_data)
                
            except Exception as ado_error:
                logger.warning(f"ADO client error, falling back to mock data: {ado_error}")
                # Fall back to mock data if ADO client fails
                from app import get_mock_analysis_data
                analysis_data = get_mock_analysis_data(work_item_id)
                return jsonify(analysis_data)
        else:
            # Use mock data if no ADO client available
            from app import get_mock_analysis_data
            analysis_data = get_mock_analysis_data(work_item_id)
            return jsonify(analysis_data)
        
    except Exception as e:
        logger.error(f"Error getting analysis data: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/analysis/<int:work_item_id>/run', methods=['POST'])
def run_analysis(work_item_id):
    """Run LLM analysis for a specific work item."""
    try:
        if not ado_client:
            return jsonify({'error': 'Azure DevOps client not connected'}), 400
        
        if not openarena_client:
            return jsonify({'error': 'OpenArena client not connected'}), 400
        
        # Get work item details
        work_item = ado_client.get_work_item(work_item_id)
        if not work_item:
            return jsonify({'error': 'Work item not found'}), 404
        
        # Check if refined work items are provided (Step 2 of workflow)
        request_data = request.get_json() or {}
        refined_work_items = request_data.get('refinedWorkItems')
        
        if refined_work_items and len(refined_work_items) > 0:
            # Step 2: Use refined work items for analysis
            logger.info(f"Using {len(refined_work_items)} refined work items for LLM analysis")
            
            # Convert refined work items to WorkItem-like objects
            all_work_items = []
            for item_data in refined_work_items:
                # Create a mock work item object with the necessary fields
                class MockWorkItem:
                    def __init__(self, data):
                        self.id = data.get('id', '')
                        self.fields = {
                            'System.Title': data.get('title', ''),
                            'System.WorkItemType': data.get('type', ''),
                            'System.State': data.get('state', ''),
                            'System.AssignedTo': data.get('assignedTo', ''),
                            'System.CreatedDate': data.get('createdDate', ''),
                            'System.AreaPath': data.get('areaPath', ''),
                            'System.CreatedBy': data.get('createdBy', ''),
                            'System.Tags': data.get('tags', ''),
                            'System.IterationPath': data.get('iterationPath', ''),
                            'Microsoft.VSTS.Common.Priority': data.get('priority', ''),
                            'System.Description': data.get('description', 'No description available')
                        }
                
                mock_item = MockWorkItem(item_data)
                all_work_items.append(mock_item)
        else:
            # Step 1: Get all work items for analysis (fallback)
            all_work_items = ado_client.get_work_items()
        
        # Perform LLM analysis
        analysis_prompt = ADOWorkItemAnalysisPrompt()
        system_prompt = analysis_prompt.create_simplified_prompt(work_item, all_work_items)
        
        # Get LLM response from OpenArena using query_workflow
        # Use the selected model workflow for analysis
        selected_model = session_config['openarena']['selected_model']
        workflow_id = session_config['openarena']['workflow_id']
        
        llm_response, cost_tracker = openarena_client.query_workflow(
            workflow_id=workflow_id,
            query=system_prompt,
            is_persistence_allowed=False
        )
        
        # Get hierarchy information
        hierarchy = ado_client.get_work_item_hierarchy(work_item_id)
        
        # Process LLM response to extract structured data
        analysis_data = process_llm_response(llm_response, main_work_item, all_work_items, hierarchy)
        
        # Add cost information to analysis data
        if cost_tracker:
            analysis_data['costInfo'] = {
                'cost': cost_tracker.get('cost', 0.0),
                'tokens': cost_tracker.get('tokens', 0),
                'model': selected_model
            }
        
        # Save analysis data to temporary file for GUI integration
        import tempfile
        temp_dir = tempfile.gettempdir()
        analysis_file = os.path.join(temp_dir, f"ado_analysis_{work_item_id}.json")
        
        with open(analysis_file, 'w', encoding='utf-8') as f:
            json.dump(analysis_data, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"Analysis data saved to {analysis_file}")
        
        return jsonify({
            'success': True,
            'message': 'Analysis completed successfully',
            'data': analysis_data
        })
        
    except Exception as e:
        logger.error(f"Error running analysis: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/work-item/<int:work_item_id>/llm-analysis', methods=['POST'])
def run_llm_analysis(work_item_id):
    """Run LLM analysis with related work items (Step 2 of analysis)."""
    try:
        data = request.get_json()
        related_items = data.get('relatedWorkItems', [])
        
        logger.info(f"[START] Starting LLM analysis for work item {work_item_id} with {len(related_items)} refined work items")
        logger.info("[SKIP] Using refined work items data - NO additional ADO calls needed!")
        
        # Convert related items to work item objects for analysis
        all_work_items = []
        if related_items:
            for item_data in related_items:
                # Create a work item object with the necessary fields
                class WorkItemForAnalysis:
                    def __init__(self, item_data):
                        self.id = item_data['id']
                        self.fields = {
                            'System.Id': item_data['id'],
                            'System.Title': item_data.get('title', 'No Title'),
                            'System.WorkItemType': item_data.get('type', 'Unknown'),
                            'System.State': item_data.get('state', 'Unknown'),
                            'System.AssignedTo': {'displayName': item_data.get('assignedTo', 'Unassigned')},
                            'System.AreaPath': item_data.get('areaPath', ''),
                            'System.IterationPath': item_data.get('iterationPath', ''),
                            'System.Description': item_data.get('description', ''),
                            'System.Reason': item_data.get('reason', ''),
                            'Microsoft.VSTS.Common.Priority': item_data.get('priority', ''),
                            'System.Tags': item_data.get('tags', ''),
                            'System.CreatedDate': item_data.get('createdDate', ''),
                            'System.ChangedDate': item_data.get('changedDate', '')
                        }
                
                all_work_items.append(WorkItemForAnalysis(item_data))
        
        # Find the main work item from the refined results (should be the first one or identified by ID)
        main_work_item = None
        for item in all_work_items:
            if item.id == work_item_id:
                main_work_item = item
                break
        
        # If main work item not found in refined results, we need to fetch it
        if not main_work_item:
            logger.warning(f"Main work item {work_item_id} not found in refined results, fetching from ADO...")
            if not ado_client:
                initialize_clients()
            
            if not ado_client:
                return jsonify({'error': 'Azure DevOps client not available'}), 500
            
            main_work_item = ado_client.get_work_item(work_item_id)
            if not main_work_item:
                return jsonify({'error': 'Work item not found'}), 404
            
            # Add to the list
            all_work_items.insert(0, main_work_item)
        else:
            logger.info(f"[SUCCESS] Using main work item from refined results - NO ADO call needed!")
        
        # Use empty hierarchy for now to avoid ADO call (can be enhanced later if needed)
        hierarchy = {'hierarchy_path': []}
        logger.info("[SKIP] Skipping hierarchy fetch - using empty hierarchy to avoid ADO call")
        
        # Perform LLM analysis
        analysis_prompt = ADOWorkItemAnalysisPrompt()
        system_prompt = analysis_prompt.create_simplified_prompt(main_work_item, all_work_items)
        
        logger.info(f"Running LLM analysis for work item {work_item_id} with {len(all_work_items)} related items")
        logger.info(f"First 5 work items being sent to LLM: {[{'id': item.id, 'title': item.fields.get('System.Title', 'No Title')[:50]} for item in all_work_items[:5]]}")
        
        # Get LLM response from OpenArena
        if openarena_client:
            try:
                # Use the selected model workflow for analysis
                selected_model = session_config['openarena']['selected_model']
                workflow_id = session_config['openarena']['workflow_id']
                
                logger.info(f"Using model for analysis: {selected_model} with workflow_id: {workflow_id}")
                
                llm_response, cost_tracker = openarena_client.query_workflow(
                    workflow_id=workflow_id,
                    query=system_prompt,
                    is_persistence_allowed=False
                )
                
                # Debug cost tracker
                logger.info(f"Cost tracker received: {cost_tracker}")
                logger.info(f"Cost tracker type: {type(cost_tracker)}")
                logger.info(f"Cost tracker keys: {list(cost_tracker.keys()) if isinstance(cost_tracker, dict) else 'Not a dict'}")
                
                # Check if response is empty or too short (likely due to timeout)
                if not llm_response or len(llm_response.strip()) < 100:
                    logger.warning(f"LLM response too short or empty ({len(llm_response) if llm_response else 0} chars), using mock response")
                    llm_response = generate_mock_llm_response(main_work_item, all_work_items)
                    cost_tracker = {}
                else:
                    logger.info(f"LLM analysis completed successfully with {len(llm_response)} characters")
                    logger.info(f"LLM response preview (first 500 chars): {llm_response[:500]}")
                
            except Exception as llm_error:
                logger.error(f"LLM analysis error: {llm_error}")
                # Fallback to mock response for development
                llm_response = generate_mock_llm_response(main_work_item, all_work_items)
                cost_tracker = {}
        else:
            # Fallback to mock response for development
            logger.warning("OpenArena client not available, using mock response")
            llm_response = generate_mock_llm_response(main_work_item, all_work_items)
            cost_tracker = {}
        
        # Process LLM response to extract structured data
        analysis_data = process_llm_response(llm_response, main_work_item, all_work_items, hierarchy)
        
        # Update cost info with actual values from cost tracker
        logger.info(f"Raw cost tracker data: {cost_tracker}")
        logger.info(f"Cost tracker keys: {list(cost_tracker.keys()) if isinstance(cost_tracker, dict) else 'Not a dict'}")
        
        if cost_tracker and isinstance(cost_tracker, dict):
            # Try different possible field names for cost and tokens
            cost = cost_tracker.get('cost') or cost_tracker.get('total_cost') or cost_tracker.get('cost_usd')
            tokens = cost_tracker.get('tokens') or cost_tracker.get('tokens_used') or cost_tracker.get('total_tokens') or cost_tracker.get('input_tokens') or cost_tracker.get('output_tokens')
            model = cost_tracker.get('model') or selected_model
            
            # If we have cost but no tokens, try to estimate tokens from cost
            if cost is not None and cost != 0 and cost != '' and (tokens is None or tokens == 0):
                # Estimate tokens based on cost and model
                if model == 'claude-4.1-opus':
                    # Claude 4.1 Opus pricing: $15 input / $75 output per million tokens
                    # Use average of input/output pricing for estimation
                    avg_cost_per_1k_tokens = 0.045  # Average of $15 and $75 per million tokens
                    estimated_tokens = int((float(cost) / avg_cost_per_1k_tokens) * 1000)
                elif model == 'gpt-5':
                    # GPT-5 pricing: $1.25 input / $10 output per million tokens
                    avg_cost_per_1k_tokens = 0.005625  # Average of $1.25 and $10 per million tokens
                    estimated_tokens = int((float(cost) / avg_cost_per_1k_tokens) * 1000)
                else:
                    # Default estimation
                    estimated_tokens = int(float(cost) * 10000)  # Rough estimate: $0.01 per 100 tokens
                
                tokens = estimated_tokens
                logger.info(f"Estimated tokens from cost: {tokens} (cost: {cost}, model: {model})")
            
            # Check if we have valid cost data (not None, not 0, not empty string)
            if cost is not None and cost != 0 and cost != '':
                analysis_data['costInfo'] = {
                    'cost': float(cost),
                    'tokens': int(tokens) if tokens is not None and tokens != 0 else 0,
                    'model': model,
                    'timestamp': datetime.now().isoformat()
                }
                logger.info(f"Using actual cost tracker data: {analysis_data['costInfo']}")
            else:
                # Fallback to estimated values if no valid cost data
                estimated_cost = 0.01 if selected_model == 'claude-4.1-opus' else 0.02
                estimated_tokens = 500 if selected_model == 'claude-4.1-opus' else 1000
                analysis_data['costInfo'] = {
                    'cost': estimated_cost,
                    'tokens': estimated_tokens,
                    'model': selected_model,
                    'timestamp': datetime.now().isoformat()
                }
                logger.info(f"Using estimated cost data: {analysis_data['costInfo']}")
        else:
            # Fallback to estimated values if no cost tracker
            estimated_cost = 0.01 if selected_model == 'claude-4.1-opus' else 0.02
            estimated_tokens = 500 if selected_model == 'claude-4.1-opus' else 1000
            analysis_data['costInfo'] = {
                'cost': estimated_cost,
                'tokens': estimated_tokens,
                'model': selected_model,
                'timestamp': datetime.now().isoformat()
            }
            logger.info(f"Using estimated cost data: {analysis_data['costInfo']}")
        
        return jsonify({
            'success': True,
            'data': analysis_data
        })
        
    except Exception as e:
        logger.error(f"Error running LLM analysis: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/work-item/<int:work_item_id>/openarena-analysis', methods=['POST'])
def run_openarena_analysis(work_item_id):
    """Run OpenArena analysis with related work items using websocket API."""
    try:
        # Get request data with better error handling
        try:
            data = request.get_json()
        except Exception as json_error:
            logger.error(f"JSON parsing error: {json_error}")
            return jsonify({'error': f'Invalid JSON data: {str(json_error)}'}), 400
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        related_items = data.get('relatedWorkItems', [])
        analysis_type = data.get('analysisType', 'work_item_analysis')
        semantic_results = data.get('semanticResults')
        work_item_data = data.get('workItem')
        selected_model = data.get('selectedModel', 'gemini2pro')
        
        logger.info(f"[START] Starting OpenArena analysis for work item {work_item_id}")
        logger.info(f"Analysis type: {analysis_type}")
        logger.info(f"Has semantic results: {semantic_results is not None}")
        logger.info(f"Has work item data: {work_item_data is not None}")
        
        # Convert related items to work item objects for analysis
        all_work_items = []
        
        # Handle AI Deep Dive case with semantic results
        if semantic_results and semantic_results.get('similar_work_items'):
            # Limit to first 20 items to avoid JSON size issues
            similar_items = semantic_results['similar_work_items'][:20]
            logger.info(f"Processing AI Deep Dive with {len(similar_items)} semantic results (limited from {len(semantic_results['similar_work_items'])})")
            for item_data in similar_items:
                # Create a work item object with the necessary fields
                class WorkItemForAnalysis:
                    def __init__(self, item_data):
                        # Sanitize data to prevent JSON parsing issues
                        def sanitize_text(text, max_length=500):
                            if not text:
                                return ''
                            return str(text).replace('\n', ' ').replace('\r', ' ').replace('"', "'").replace('\\', '/')[:max_length]
                        
                        self.id = item_data['id']
                        self.fields = {
                            'System.Id': item_data['id'],
                            'System.Title': sanitize_text(item_data.get('title', 'No Title'), 200),
                            'System.WorkItemType': sanitize_text(item_data.get('workItemType', 'Unknown'), 50),
                            'System.State': sanitize_text(item_data.get('state', 'Unknown'), 50),
                            'System.AssignedTo': {'displayName': sanitize_text(item_data.get('assignedTo', 'Unassigned'), 100)},
                            'System.AreaPath': sanitize_text(item_data.get('areaPath', ''), 200),
                            'System.IterationPath': sanitize_text(item_data.get('iterationPath', ''), 200),
                            'System.Description': sanitize_text(item_data.get('description', ''), 1000),
                            'System.Reason': sanitize_text(item_data.get('reason', ''), 200),
                            'Microsoft.VSTS.Common.Priority': str(item_data.get('priority', '')),
                            'System.Tags': sanitize_text(item_data.get('tags', ''), 200),
                            'System.CreatedDate': sanitize_text(item_data.get('createdDate', ''), 50),
                            'System.ChangedDate': sanitize_text(item_data.get('changedDate', ''), 50)
                        }
                
                all_work_items.append(WorkItemForAnalysis(item_data))
        elif related_items:
            logger.info(f"Processing traditional analysis with {len(related_items)} related items")
            for item_data in related_items:
                # Ensure item_data is a dictionary, not a string
                if isinstance(item_data, str):
                    logger.warning(f"Skipping string item: {item_data}")
                    continue
                    
                # Create a work item object with the necessary fields
                class WorkItemForAnalysis:
                    def __init__(self, item_data):
                        self.id = item_data['id']
                        self.fields = {
                            'System.Id': item_data['id'],
                            'System.Title': item_data.get('title', 'No Title'),
                            'System.WorkItemType': item_data.get('type', 'Unknown'),
                            'System.State': item_data.get('state', 'Unknown'),
                            'System.AssignedTo': {'displayName': item_data.get('assignedTo', 'Unassigned')},
                            'System.AreaPath': item_data.get('areaPath', ''),
                            'System.IterationPath': item_data.get('iterationPath', ''),
                            'System.Description': item_data.get('description', ''),
                            'System.Reason': item_data.get('reason', ''),
                            'Microsoft.VSTS.Common.Priority': item_data.get('priority', ''),
                            'System.Tags': item_data.get('tags', ''),
                            'System.CreatedDate': item_data.get('createdDate', ''),
                            'System.ChangedDate': item_data.get('changedDate', '')
                        }
                
                all_work_items.append(WorkItemForAnalysis(item_data))
        
        # Find the main work item from the refined results
        main_work_item = None
        for item in all_work_items:
            if item.id == work_item_id:
                main_work_item = item
                break
        
        # If main work item not found in refined results, we need to fetch it
        if not main_work_item:
            logger.warning(f"Main work item {work_item_id} not found in refined results, fetching from ADO...")
            if not ado_client:
                initialize_clients()
            
            if not ado_client:
                return jsonify({'error': 'Azure DevOps client not available'}), 500
            
            main_work_item = ado_client.get_work_item(work_item_id)
            if not main_work_item:
                return jsonify({'error': 'Work item not found'}), 404
            
            # Add to the list
            all_work_items.insert(0, main_work_item)
        else:
            logger.info(f"[SUCCESS] Using main work item from refined results - NO ADO call needed!")
        
        # Use empty hierarchy for now to avoid ADO call
        hierarchy = {'hierarchy_path': []}
        logger.info("[SKIP] Skipping hierarchy fetch - using empty hierarchy to avoid ADO call")
        
        # Perform OpenArena analysis using optimized prompt for AI Deep Dive
        analysis_prompt = ADOWorkItemAnalysisPrompt()
        
        # For AI Deep Dive with many work items, use optimized prompt
        if analysis_type == 'ai_deep_dive' and len(all_work_items) > 50:
            logger.info(f"Using optimized prompt for AI Deep Dive with {len(all_work_items)} work items")
            system_prompt = analysis_prompt.create_optimized_prompt(main_work_item, all_work_items, max_items=50)
        else:
            logger.info(f"Using standard prompt for {analysis_type} with {len(all_work_items)} work items")
            system_prompt = analysis_prompt.create_system_prompt(main_work_item, all_work_items)
        
        logger.info(f"Running OpenArena analysis for work item {work_item_id} with {len(all_work_items)} related items")
        logger.info(f"System prompt length: {len(system_prompt)} characters")
        
        # DEBUG: Print full system prompt
        print("\n" + "="*100)
        print("FULL SYSTEM PROMPT:")
        print("="*100)
        print(system_prompt)
        print("="*100)
        print("END OF SYSTEM PROMPT")
        print("="*100 + "\n")
        
        # Get OpenArena response
        if openarena_client:
            try:
                # Use the selected model workflow for analysis
                selected_model = session_config['openarena']['selected_model']
                workflow_id = session_config['openarena']['workflow_id']
                
                logger.info(f"Using OpenArena model: {selected_model} with workflow_id: {workflow_id}")
                
                llm_response, cost_tracker = openarena_client.query_workflow(
                    workflow_id=workflow_id,
                    query=system_prompt,
                    is_persistence_allowed=False
                )
                
                # Debug cost tracker
                logger.info(f"OpenArena cost tracker received: {cost_tracker}")
                logger.info(f"OpenArena response length: {len(llm_response) if llm_response else 0} characters")
                
                # Check if response is empty or too short
                if not llm_response or len(llm_response.strip()) < 100:
                    logger.warning(f"OpenArena response too short or empty ({len(llm_response) if llm_response else 0} chars), using mock response")
                    llm_response = generate_mock_llm_response(main_work_item, all_work_items)
                    cost_tracker = {}
                else:
                    logger.info(f"OpenArena analysis completed successfully with {len(llm_response)} characters")
                
            except Exception as openarena_error:
                logger.error(f"OpenArena analysis error: {openarena_error}")
                # Fallback to mock response for development
                llm_response = generate_mock_llm_response(main_work_item, all_work_items)
                cost_tracker = {}
        else:
            # Fallback to mock response for development
            logger.warning("OpenArena client not available, using mock response")
            llm_response = generate_mock_llm_response(main_work_item, all_work_items)
            cost_tracker = {}
        
        # Process OpenArena response using the advanced parser
        try:
            from llm_response_parser import AdvancedLLMResponseParser, convert_parsed_analysis_to_dict
            
            # Create parser instance
            parser = AdvancedLLMResponseParser()
            
            # Parse the OpenArena response
            parsed_analysis = parser.parse_response(llm_response, all_work_items, main_work_item)
            
            # Convert to the expected format with raw analysis text
            analysis_data = convert_parsed_analysis_to_dict(parsed_analysis, llm_response)
            
            # Update cost info with actual values from cost tracker
            logger.info(f"Raw OpenArena cost tracker data: {cost_tracker}")
            logger.info(f"Cost tracker keys: {list(cost_tracker.keys()) if isinstance(cost_tracker, dict) else 'Not a dict'}")
            
            if cost_tracker and isinstance(cost_tracker, dict):
                # Try different possible field names for cost and tokens
                cost = cost_tracker.get('cost') or cost_tracker.get('total_cost') or cost_tracker.get('cost_usd')
                tokens = cost_tracker.get('tokens') or cost_tracker.get('tokens_used') or cost_tracker.get('total_tokens') or cost_tracker.get('input_tokens') or cost_tracker.get('output_tokens')
                model = cost_tracker.get('model') or selected_model
                
                # If we have cost but no tokens, try to estimate tokens from cost
                if cost is not None and cost != 0 and cost != '' and (tokens is None or tokens == 0):
                    # Estimate tokens based on cost and model
                    if model == 'claude-4.1-opus':
                        # Claude 4.1 Opus pricing: $15 input / $75 output per million tokens
                        # Use average of input/output pricing for estimation
                        avg_cost_per_1k_tokens = 0.045  # Average of $15 and $75 per million tokens
                        estimated_tokens = int((float(cost) / avg_cost_per_1k_tokens) * 1000)
                    elif model == 'gpt-5':
                        # GPT-5 pricing: $1.25 input / $10 output per million tokens
                        avg_cost_per_1k_tokens = 0.005625  # Average of $1.25 and $10 per million tokens
                        estimated_tokens = int((float(cost) / avg_cost_per_1k_tokens) * 1000)
                    else:
                        # Default estimation
                        estimated_tokens = int(float(cost) * 10000)  # Rough estimate: $0.01 per 100 tokens
                    
                    tokens = estimated_tokens
                    logger.info(f"Estimated tokens from cost: {tokens} (cost: {cost}, model: {model})")
                
                # Check if we have valid cost data (not None, not 0, not empty string)
                if cost is not None and cost != 0 and cost != '':
                    analysis_data['costInfo'] = {
                        'cost': float(cost),
                        'tokens': int(tokens) if tokens is not None and tokens != 0 else 0,
                        'model': model,
                        'timestamp': datetime.now().isoformat()
                    }
                    logger.info(f"Using actual OpenArena cost tracker data: {analysis_data['costInfo']}")
                else:
                    # Fallback to estimated values if no valid cost data
                    estimated_cost = 0.05 if selected_model == 'claude-4.1-opus' else 0.08
                    estimated_tokens = 2000 if selected_model == 'claude-4.1-opus' else 3000
                    analysis_data['costInfo'] = {
                        'cost': estimated_cost,
                        'tokens': estimated_tokens,
                        'model': selected_model,
                        'timestamp': datetime.now().isoformat()
                    }
                    logger.info(f"Using estimated OpenArena cost data: {analysis_data['costInfo']}")
            else:
                # Fallback to estimated values if no cost tracker
                estimated_cost = 0.05 if selected_model == 'claude-4.1-opus' else 0.08
                estimated_tokens = 2000 if selected_model == 'claude-4.1-opus' else 3000
                analysis_data['costInfo'] = {
                    'cost': estimated_cost,
                    'tokens': estimated_tokens,
                    'model': selected_model,
                    'timestamp': datetime.now().isoformat()
                }
                logger.info(f"Using estimated OpenArena cost data: {analysis_data['costInfo']}")
            
            # Add model and timestamp info
            analysis_data['modelUsed'] = selected_model
            analysis_data['timestamp'] = datetime.now().isoformat()
            
            # Add raw system prompt for debugging/inspection
            analysis_data['systemPrompt'] = system_prompt
            
            return jsonify({
                'success': True,
                'data': analysis_data
            })
            
        except ImportError as parser_error:
            logger.error(f"Advanced parser not available, using fallback: {parser_error}")
            # Fallback to simple processing
            analysis_data = process_llm_response_fallback(llm_response, main_work_item, all_work_items, hierarchy)
            analysis_data['analysisResults'] = llm_response
            analysis_data['modelUsed'] = selected_model
            analysis_data['timestamp'] = datetime.now().isoformat()
            
            # Add raw system prompt for debugging/inspection
            analysis_data['systemPrompt'] = system_prompt
            
            return jsonify({
                'success': True,
                'data': analysis_data
            })
        
    except Exception as e:
        logger.error(f"Error running OpenArena analysis: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

# ===== AUTO MODEL SELECTION LOGIC =====

def analyze_work_item_complexity(work_item):
    """Analyze work item complexity to help with model selection."""
    complexity_score = 0
    factors = []
    
    try:
        # Check work item type
        work_item_type = work_item.get('fields', {}).get('System.WorkItemType', '').lower()
        if work_item_type in ['epic', 'initiative']:
            complexity_score += 3
            factors.append('Epic/Initiative type')
        elif work_item_type in ['feature', 'enhancement']:
            complexity_score += 2
            factors.append('Feature/Enhancement type')
        elif work_item_type in ['bug', 'defect']:
            complexity_score += 1
            factors.append('Bug/Defect type')
        else:
            complexity_score += 1.5
            factors.append('Standard work item type')
        
        # Check description length
        description = work_item.get('fields', {}).get('System.Description', '')
        if isinstance(description, str):
            desc_len = len(description.strip())
            if desc_len > 1000:
                complexity_score += 2
                factors.append('Long description (1000+ chars)')
            elif desc_len > 500:
                complexity_score += 1
                factors.append('Medium description (500-1000 chars)')
        
        # Check acceptance criteria length
        acceptance_criteria = work_item.get('fields', {}).get('Microsoft.VSTS.Common.AcceptanceCriteria', '')
        if isinstance(acceptance_criteria, str) and len(acceptance_criteria.strip()) > 200:
            complexity_score += 1
            factors.append('Detailed acceptance criteria')
        
        # Check for code/technical keywords
        all_text = ' '.join([
            work_item.get('fields', {}).get('System.Title', ''),
            str(description),
            str(acceptance_criteria)
        ]).lower()
        
        technical_keywords = ['code', 'api', 'database', 'architecture', 'performance', 'security', 
                            'integration', 'migration', 'refactor', 'optimization', 'algorithm']
        code_keywords = ['function', 'class', 'method', 'variable', 'sql', 'javascript', 'python', 'css']
        
        if any(keyword in all_text for keyword in code_keywords):
            complexity_score += 2
            factors.append('Code-related content')
        elif any(keyword in all_text for keyword in technical_keywords):
            complexity_score += 1
            factors.append('Technical content')
        
        # Check story points if available
        story_points = work_item.get('fields', {}).get('Microsoft.VSTS.Scheduling.StoryPoints')
        if story_points:
            try:
                points = float(story_points)
                if points >= 8:
                    complexity_score += 2
                    factors.append(f'High story points ({points})')
                elif points >= 5:
                    complexity_score += 1
                    factors.append(f'Medium story points ({points})')
            except (ValueError, TypeError):
                pass
        
        # Determine complexity level
        if complexity_score >= 6:
            complexity = 'high'
        elif complexity_score >= 3:
            complexity = 'medium'
        else:
            complexity = 'low'
            
        return {
            'complexity': complexity,
            'score': complexity_score,
            'factors': factors
        }
        
    except Exception as e:
        logger.error(f"Error analyzing work item complexity: {e}")
        return {
            'complexity': 'medium',
            'score': 3,
            'factors': ['Default - analysis error']
        }

def get_model_selection_matrix():
    """Define the model selection matrix based on work item type and complexity."""
    return {
        'speed': {
            'bug': {'low': 'llama-3-70b', 'medium': 'gpt-5', 'high': 'gpt-5'},
            'user story': {'low': 'llama-3-70b', 'medium': 'gpt-5', 'high': 'gemini-2.5-pro'},
            'feature': {'low': 'gpt-5', 'medium': 'gemini-2.5-pro', 'high': 'claude-4.1-opus'},
            'epic': {'low': 'gemini-2.5-pro', 'medium': 'claude-4.1-opus', 'high': 'claude-4.1-opus'},
            'default': {'low': 'gpt-5', 'medium': 'gpt-5', 'high': 'gemini-2.5-pro'}
        },
        'cost': {
            'bug': {'low': 'llama-3-70b', 'medium': 'llama-3-70b', 'high': 'gpt-5'},
            'user story': {'low': 'llama-3-70b', 'medium': 'gpt-5', 'high': 'gpt-5'},
            'feature': {'low': 'llama-3-70b', 'medium': 'gpt-5', 'high': 'gemini-2.5-pro'},
            'epic': {'low': 'gpt-5', 'medium': 'gemini-2.5-pro', 'high': 'claude-4.1-opus'},
            'default': {'low': 'llama-3-70b', 'medium': 'gpt-5', 'high': 'gpt-5'}
        },
        'quality': {
            'bug': {'low': 'gpt-5', 'medium': 'claude-4.1-opus', 'high': 'claude-4.1-opus'},
            'user story': {'low': 'gemini-2.5-pro', 'medium': 'claude-4.1-opus', 'high': 'claude-4.1-opus'},
            'feature': {'low': 'gemini-2.5-pro', 'medium': 'claude-4.1-opus', 'high': 'claude-4.1-opus'},
            'epic': {'low': 'claude-4.1-opus', 'medium': 'claude-4.1-opus', 'high': 'claude-4.1-opus'},
            'default': {'low': 'gpt-5', 'medium': 'claude-4.1-opus', 'high': 'claude-4.1-opus'}
        },
        'coding': {
            'bug': {'low': 'gemini-2.5-pro', 'medium': 'gemini-2.5-pro', 'high': 'claude-4.1-opus'},
            'user story': {'low': 'gemini-2.5-pro', 'medium': 'gemini-2.5-pro', 'high': 'claude-4.1-opus'},
            'feature': {'low': 'gemini-2.5-pro', 'medium': 'gemini-2.5-pro', 'high': 'claude-4.1-opus'},
            'epic': {'low': 'gemini-2.5-pro', 'medium': 'claude-4.1-opus', 'high': 'claude-4.1-opus'},
            'default': {'low': 'gemini-2.5-pro', 'medium': 'gemini-2.5-pro', 'high': 'claude-4.1-opus'}
        },
        'balanced': {
            'bug': {'low': 'llama-3-70b', 'medium': 'gpt-5', 'high': 'claude-4.1-opus'},
            'user story': {'low': 'gpt-5', 'medium': 'gemini-2.5-pro', 'high': 'claude-4.1-opus'},
            'feature': {'low': 'gpt-5', 'medium': 'gemini-2.5-pro', 'high': 'claude-4.1-opus'},
            'epic': {'low': 'gemini-2.5-pro', 'medium': 'claude-4.1-opus', 'high': 'claude-4.1-opus'},
            'default': {'low': 'gpt-5', 'medium': 'gpt-5', 'high': 'gemini-2.5-pro'}
        }
    }

def auto_select_model(work_items, user_priority='balanced'):
    """Automatically select the best model based on work items and user priority."""
    try:
        if not work_items:
            return {
                'success': False,
                'error': 'No work items provided for analysis',
                'selected_model': session_config['auto_selection']['fallback_model']
            }
        
        # Analyze complexity of all work items
        total_complexity_score = 0
        analysis_details = []
        work_item_types = []
        
        for work_item in work_items:
            complexity_analysis = analyze_work_item_complexity(work_item)
            total_complexity_score += complexity_analysis['score']
            analysis_details.append(complexity_analysis)
            
            work_item_type = work_item.get('fields', {}).get('System.WorkItemType', '').lower()
            work_item_types.append(work_item_type)
        
        # Determine overall complexity
        avg_complexity_score = total_complexity_score / len(work_items)
        if avg_complexity_score >= 6:
            overall_complexity = 'high'
        elif avg_complexity_score >= 3:
            overall_complexity = 'medium'
        else:
            overall_complexity = 'low'
        
        # Determine primary work item type
        most_common_type = max(set(work_item_types), key=work_item_types.count) if work_item_types else 'default'
        
        # Map work item types to our matrix keys
        type_mapping = {
            'bug': 'bug',
            'user story': 'user story',
            'feature': 'feature',
            'epic': 'epic',
            'initiative': 'epic',
            'task': 'user story',
            'enhancement': 'feature'
        }
        
        matrix_type = type_mapping.get(most_common_type, 'default')
        
        # Get selection matrix and choose model
        selection_matrix = get_model_selection_matrix()
        priority_matrix = selection_matrix.get(user_priority, selection_matrix['balanced'])
        type_matrix = priority_matrix.get(matrix_type, priority_matrix['default'])
        selected_model = type_matrix.get(overall_complexity, 'claude-4.1-opus')
        
        # Verify model availability
        try:
            from src.openarena.config.env_config import (
                OPENARENA_CLAUDE41OPUS_WORKFLOW_ID,
                OPENARENA_GPT5_WORKFLOW_ID,
                OPENARENA_GEMINI25PRO_WORKFLOW_ID,
                OPENARENA_LLAMA3_70B_WORKFLOW_ID
            )
            
            model_workflow_map = {
                'claude-4.1-opus': OPENARENA_CLAUDE41OPUS_WORKFLOW_ID,
                'gpt-5': OPENARENA_GPT5_WORKFLOW_ID,
                'gemini-2.5-pro': OPENARENA_GEMINI25PRO_WORKFLOW_ID,
                'llama-3-70b': OPENARENA_LLAMA3_70B_WORKFLOW_ID
            }
            
            # Check if selected model is available, fallback if not
            if selected_model not in model_workflow_map or not model_workflow_map[selected_model]:
                # Try fallback models in order of preference
                fallback_order = ['claude-4.1-opus', 'gpt-5', 'gemini-2.5-pro', 'llama-3-70b']
                for fallback_model in fallback_order:
                    if fallback_model in model_workflow_map and model_workflow_map[fallback_model]:
                        selected_model = fallback_model
                        break
                else:
                    return {
                        'success': False,
                        'error': 'No available models found',
                        'selected_model': None
                    }
            
            return {
                'success': True,
                'selected_model': selected_model,
                'reasoning': {
                    'work_item_count': len(work_items),
                    'primary_type': most_common_type,
                    'overall_complexity': overall_complexity,
                    'avg_complexity_score': round(avg_complexity_score, 2),
                    'user_priority': user_priority,
                    'analysis_details': analysis_details[:3]  # Limit to first 3 for brevity
                }
            }
            
        except ImportError as e:
            logger.error(f"Error importing model configuration for auto-selection: {e}")
            return {
                'success': False,
                'error': 'Model configuration not available',
                'selected_model': session_config['auto_selection']['fallback_model']
            }
            
    except Exception as e:
        logger.error(f"Error in auto_select_model: {e}")
        return {
            'success': False,
            'error': str(e),
            'selected_model': session_config['auto_selection']['fallback_model']
        }

# ===== MODEL SELECTION APIS =====

@app.route('/api/models/available')
def get_available_models():
    """Get available LLM models from actual configuration."""
    try:
        # Import the configured models
        from src.openarena.config.env_config import (
            OPENARENA_CLAUDE41OPUS_WORKFLOW_ID,
            OPENARENA_GPT5_WORKFLOW_ID,
            OPENARENA_GEMINI25PRO_WORKFLOW_ID,
            OPENARENA_LLAMA3_70B_WORKFLOW_ID
        )
        
        # Define models based on actual configuration
        available_models = []
        
        # Claude 4.1 Opus
        if OPENARENA_CLAUDE41OPUS_WORKFLOW_ID:
            available_models.append({
                'id': 'claude-4.1-opus',
                'name': 'Claude 4.1 Opus',
                'description': 'Most intelligent model to date - Hybrid reasoning model with 200K context window. Leader on SWE-bench.',
                'workflow_id': OPENARENA_CLAUDE41OPUS_WORKFLOW_ID,
                'capabilities': ['complex-agent-applications', 'coding', 'extended-thinking'],
                'speed': '44.3 tokens/sec',
                'cost': 'Very High'
            })
        
        # GPT-5
        if OPENARENA_GPT5_WORKFLOW_ID:
            available_models.append({
                'id': 'gpt-5',
                'name': 'GPT-5',
                'description': 'Smartest, fastest, most useful model - 74.9% on SWE-bench with unified reasoning system.',
                'workflow_id': OPENARENA_GPT5_WORKFLOW_ID,
                'capabilities': ['coding-collaborator', 'superior-coding', 'reduced-hallucinations'],
                'speed': 'Fast',
                'cost': 'Medium'
            })
        
        # Gemini 2.5 Pro
        if OPENARENA_GEMINI25PRO_WORKFLOW_ID:
            available_models.append({
                'id': 'gemini-2.5-pro',
                'name': 'Gemini 2.5 Pro',
                'description': 'Most advanced model for coding - 1M token context with reasoning capabilities.',
                'workflow_id': OPENARENA_GEMINI25PRO_WORKFLOW_ID,
                'capabilities': ['development-work', 'code-generation', 'large-scale-automation'],
                'speed': 'Fast',
                'cost': 'Medium'
            })
        
        # Llama 3 70b
        if OPENARENA_LLAMA3_70B_WORKFLOW_ID:
            available_models.append({
                'id': 'llama-3-70b',
                'name': 'Llama 3 70b',
                'description': 'Most capable openly available LLM - 70B parameters optimized for dialogue and chat.',
                'workflow_id': OPENARENA_LLAMA3_70B_WORKFLOW_ID,
                'capabilities': ['conversational-ai', 'code-generation', 'text-summarization'],
                'speed': '42.2 tokens/sec',
                'cost': 'Low'
            })
        
        logger.info(f"Returning {len(available_models)} configured models")
        return jsonify(available_models)
        
    except ImportError as e:
        logger.error(f"Error importing model configuration: {e}")
        # Fallback to basic models if configuration can't be loaded
        return jsonify([
            {
                'id': 'default',
                'name': 'Default Model',
                'description': 'Default model (configuration error)',
                'workflow_id': None,
                'capabilities': ['basic'],
                'speed': 'Unknown',
                'cost': 'Unknown'
            }
        ])
    except Exception as e:
        logger.error(f"Error getting available models: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/models/current')
def get_current_model():
    """Get currently selected model."""
    current_model = session_config['openarena']['selected_model']
    workflow_id = session_config['openarena']['workflow_id']
    
    logger.info(f"Current model requested: {current_model}, workflow_id: {workflow_id}")
    
    return jsonify({
        'model': current_model,
        'workflow_id': workflow_id
    })

@app.route('/api/models/select', methods=['POST'])
def select_model():
    """Select a specific model."""
    try:
        data = request.json
        model_id = data.get('model')
        
        if not model_id:
            return jsonify({'error': 'Model ID is required'}), 400
        
        # Verify the model exists in available models
        try:
            from src.openarena.config.env_config import (
                OPENARENA_CLAUDE41OPUS_WORKFLOW_ID,
                OPENARENA_GPT5_WORKFLOW_ID,
                OPENARENA_GEMINI25PRO_WORKFLOW_ID,
                OPENARENA_LLAMA3_70B_WORKFLOW_ID
            )
            
            # Map model IDs to workflow IDs
            model_workflow_map = {
                'claude-4.1-opus': OPENARENA_CLAUDE41OPUS_WORKFLOW_ID,
                'gpt-5': OPENARENA_GPT5_WORKFLOW_ID,
                'gemini-2.5-pro': OPENARENA_GEMINI25PRO_WORKFLOW_ID,
                'llama-3-70b': OPENARENA_LLAMA3_70B_WORKFLOW_ID
            }
            
            if model_id not in model_workflow_map:
                return jsonify({'error': f'Model {model_id} is not available'}), 400
            
            workflow_id = model_workflow_map[model_id]
            if not workflow_id:
                return jsonify({'error': f'Model {model_id} is not properly configured (missing workflow ID)'}), 400
            
            # Update session config
            session_config['openarena']['selected_model'] = model_id
            session_config['openarena']['workflow_id'] = workflow_id
            
            logger.info(f"Model selected: {model_id} with workflow ID: {workflow_id}")
            logger.info(f"Session config updated: {session_config['openarena']}")
            
            return jsonify({
                'success': True,
                'message': f'Model {model_id} selected successfully',
                'model': model_id,
                'workflow_id': workflow_id
            })
            
        except ImportError as e:
            logger.error(f"Error importing model configuration: {e}")
            return jsonify({'error': 'Model configuration error'}), 500
        
    except Exception as e:
        logger.error(f"Error selecting model: {e}")
        return jsonify({'error': str(e)}), 500

# ===== AUTO SELECTION API ENDPOINTS =====

@app.route('/api/models/auto-select', methods=['POST'])
def api_auto_select_model():
    """API endpoint to automatically select a model based on work items."""
    try:
        data = request.json
        work_items = data.get('work_items', [])
        user_priority = data.get('user_priority', session_config['auto_selection']['user_priority'])
        
        if not work_items:
            return jsonify({'error': 'work_items are required for auto-selection'}), 400
        
        # Perform auto-selection
        selection_result = auto_select_model(work_items, user_priority)
        
        if selection_result['success']:
            # Update session config with auto-selected model
            selected_model = selection_result['selected_model']
            
            # Get workflow ID for the selected model
            from src.openarena.config.env_config import (
                OPENARENA_CLAUDE41OPUS_WORKFLOW_ID,
                OPENARENA_GPT5_WORKFLOW_ID,
                OPENARENA_GEMINI25PRO_WORKFLOW_ID,
                OPENARENA_LLAMA3_70B_WORKFLOW_ID
            )
            
            model_workflow_map = {
                'claude-4.1-opus': OPENARENA_CLAUDE41OPUS_WORKFLOW_ID,
                'gpt-5': OPENARENA_GPT5_WORKFLOW_ID,
                'gemini-2.5-pro': OPENARENA_GEMINI25PRO_WORKFLOW_ID,
                'llama-3-70b': OPENARENA_LLAMA3_70B_WORKFLOW_ID
            }
            
            workflow_id = model_workflow_map.get(selected_model)
            
            # Update session configuration
            session_config['openarena']['selected_model'] = selected_model
            session_config['openarena']['workflow_id'] = workflow_id
            session_config['auto_selection']['last_auto_selected'] = selected_model
            
            logger.info(f"Auto-selected model: {selected_model} based on {len(work_items)} work items")
            
            return jsonify({
                'success': True,
                'selected_model': selected_model,
                'workflow_id': workflow_id,
                'reasoning': selection_result['reasoning'],
                'message': f'Auto-selected {selected_model} based on work item analysis'
            })
        else:
            return jsonify({
                'success': False,
                'error': selection_result['error'],
                'fallback_model': selection_result.get('selected_model')
            }), 400
            
    except Exception as e:
        logger.error(f"Error in auto-select API: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/models/auto-select/preview', methods=['POST'])
def api_preview_auto_selection():
    """Preview what model would be auto-selected without actually selecting it."""
    try:
        data = request.json
        work_items = data.get('work_items', [])
        user_priority = data.get('user_priority', session_config['auto_selection']['user_priority'])
        
        if not work_items:
            return jsonify({'error': 'work_items are required for preview'}), 400
        
        # Perform auto-selection preview
        selection_result = auto_select_model(work_items, user_priority)
        
        return jsonify({
            'success': selection_result['success'],
            'preview_model': selection_result.get('selected_model'),
            'reasoning': selection_result.get('reasoning'),
            'error': selection_result.get('error')
        })
        
    except Exception as e:
        logger.error(f"Error in auto-select preview API: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/auto-selection/settings', methods=['GET'])
def get_auto_selection_settings():
    """Get current auto-selection settings."""
    return jsonify(session_config['auto_selection'])

@app.route('/api/auto-selection/settings', methods=['POST'])
def update_auto_selection_settings():
    """Update auto-selection settings."""
    try:
        data = request.json
        
        if 'enabled' in data:
            session_config['auto_selection']['enabled'] = bool(data['enabled'])
        
        if 'user_priority' in data:
            valid_priorities = ['speed', 'cost', 'quality', 'coding', 'balanced']
            if data['user_priority'] in valid_priorities:
                session_config['auto_selection']['user_priority'] = data['user_priority']
            else:
                return jsonify({'error': f'Invalid priority. Must be one of: {valid_priorities}'}), 400
        
        if 'fallback_model' in data:
            session_config['auto_selection']['fallback_model'] = data['fallback_model']
        
        logger.info(f"Auto-selection settings updated: {session_config['auto_selection']}")
        
        return jsonify({
            'success': True,
            'settings': session_config['auto_selection'],
            'message': 'Auto-selection settings updated successfully'
        })
        
    except Exception as e:
        logger.error(f"Error updating auto-selection settings: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/models/complexity-analysis', methods=['POST'])
def api_analyze_work_item_complexity():
    """Analyze work item complexity for debugging/preview purposes."""
    try:
        data = request.json
        work_items = data.get('work_items', [])
        
        if not work_items:
            return jsonify({'error': 'work_items are required'}), 400
        
        analysis_results = []
        for work_item in work_items:
            complexity_analysis = analyze_work_item_complexity(work_item)
            work_item_title = work_item.get('fields', {}).get('System.Title', 'Untitled')
            analysis_results.append({
                'title': work_item_title,
                'id': work_item.get('id'),
                'complexity': complexity_analysis
            })
        
        return jsonify({
            'success': True,
            'analyses': analysis_results,
            'total_work_items': len(work_items)
        })
        
    except Exception as e:
        logger.error(f"Error in complexity analysis API: {e}")
        return jsonify({'error': str(e)}), 500

# ===== HELPER FUNCTIONS (from existing app.py) =====

def load_analysis_data_from_gui(work_item_id):
    """Load analysis data from GUI if available."""
    try:
        import tempfile
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

def process_llm_response(llm_response, selected_work_item, all_work_items, hierarchy):
    """Process LLM response using the advanced parser for accurate data extraction."""
    try:
        # Import from existing app.py
        from app import process_llm_response as process_response
        return process_response(llm_response, selected_work_item, all_work_items, hierarchy)
    except Exception as e:
        logger.error(f"Error in LLM response processing: {e}")
        # Fallback to simple processing
        return {
            'selectedWorkItem': {
                'id': selected_work_item.id,
                'title': selected_work_item.fields.get('System.Title', 'No Title'),
                'type': selected_work_item.fields.get('System.WorkItemType', 'Unknown'),
                'state': selected_work_item.fields.get('System.State', 'Unknown')
            },
            'hierarchy': [],
            'relatedWorkItems': [],
            'analysisInsights': {'risks': [], 'opportunities': [], 'recommendations': []}
            # costInfo will be added by the calling function with actual values
        }

def generate_mock_llm_response(work_item, all_work_items):
    """Generate a mock LLM response for development/testing."""
    from app import generate_mock_llm_response as mock_response
    return mock_response(work_item, all_work_items)

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
            # Import with correct path
            from src.openarena.config.env_config import (
                OPENARENA_ESSO_TOKEN,
                OPENARENA_WEBSOCKET_URL,
                OPENARENA_GPT5_WORKFLOW_ID
            )
            config_data['openarena']['esso_token'] = OPENARENA_ESSO_TOKEN
            config_data['openarena']['websocket_url'] = OPENARENA_WEBSOCKET_URL
            config_data['openarena']['workflow_id'] = OPENARENA_GPT5_WORKFLOW_ID
        except ImportError as e:
            logger.warning(f"Could not import OpenArena config: {e}")
            # Fallback: try to read directly from file
            try:
                env_config_file = os.path.join(os.path.dirname(__file__), '..', 'src', 'openarena', 'config', 'env_config.py')
                if os.path.exists(env_config_file):
                    with open(env_config_file, 'r') as f:
                        content = f.read()
                    
                    # Extract values using regex
                    import re
                    esso_match = re.search(r'OPENARENA_ESSO_TOKEN = "([^"]*)"', content)
                    websocket_match = re.search(r'OPENARENA_WEBSOCKET_URL="([^"]*)"', content)
                    workflow_match = re.search(r'OPENARENA_GPT5_WORKFLOW_ID="([^"]*)"', content)
                    
                    if esso_match:
                        config_data['openarena']['esso_token'] = esso_match.group(1)
                    if websocket_match:
                        config_data['openarena']['websocket_url'] = websocket_match.group(1)
                    if workflow_match:
                        config_data['openarena']['workflow_id'] = workflow_match.group(1)
                        
                    logger.info("Successfully loaded OpenArena config from file directly")
            except Exception as file_error:
                logger.error(f"Failed to read OpenArena config file: {file_error}")
        
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

@app.route('/api/debug/wiql', methods=['POST'])
def debug_wiql_query():
    """Debug endpoint to test WIQL queries directly."""
    try:
        data = request.get_json()
        wiql_query = data.get('wiql_query')
        
        if not wiql_query:
            return jsonify({'error': 'wiql_query is required'}), 400
        
        if not ado_client:
            return jsonify({'error': 'ADO client not connected'}), 400
        
        # Execute the query
        work_item_client = ado_client.connection.clients.get_work_item_tracking_client()
        wiql = {"query": wiql_query}
        query_result = work_item_client.query_by_wiql(wiql)
        
        results = []
        if query_result and hasattr(query_result, 'work_items') and query_result.work_items:
            # Get full work item details for each reference
            work_item_ids = [item.id for item in query_result.work_items]
            if work_item_ids:
                work_items = work_item_client.get_work_items(work_item_ids)
                for item in work_items:
                    results.append({
                        'id': item.id,
                        'title': item.fields.get('System.Title', ''),
                        'workItemType': item.fields.get('System.WorkItemType', ''),
                        'state': item.fields.get('System.State', ''),
                        'areaPath': item.fields.get('System.AreaPath', ''),
                        'createdDate': item.fields.get('System.CreatedDate', ''),
                        'assignedTo': item.fields.get('System.AssignedTo', ''),
                        'createdBy': item.fields.get('System.CreatedBy', '')
                    })
        
        return jsonify({
            'success': True,
            'count': len(results),
            'work_items': results
        })
        
    except Exception as e:
        logger.error(f"Error in debug WIQL query: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/debug/team-detection/<int:work_item_id>')
def debug_team_detection(work_item_id):
    """Debug endpoint to test team group detection logic."""
    try:
        if not ado_client:
            return jsonify({'error': 'ADO DevOps client not connected'}), 400
        
        # Get the project name from session config
        project_name = session_config['azure_devops'].get('project')
        if not project_name:
            return jsonify({'error': 'No project selected'}), 400

        # Get the work item
        work_item_client = ado_client.connection.clients.get_work_item_tracking_client()
        selected_work_item = work_item_client.get_work_item(work_item_id)
        
        # Get all teams
        all_teams = ado_client.get_teams(project_name)
        all_team_names = [team.name for team in all_teams]
        
        # Extract team information
        area_path = selected_work_item.fields.get('System.AreaPath', '')
        selected_team_name = ''
        group_teams = []
        
        if area_path:
            path_parts = area_path.split('\\')
            if len(path_parts) >= 2:
                selected_team_name = path_parts[-1]
        
        # Test team group detection logic
        debug_info = {
            'work_item_id': work_item_id,
            'area_path': area_path,
            'selected_team_name': selected_team_name,
            'all_teams_count': len(all_team_names),
            'all_teams': all_team_names,
            'detection_logic': []
        }
        
        # Test accessibility detection
        if 'accessibility' in selected_team_name.lower() or 'a11y' in selected_team_name.lower():
            debug_info['detection_logic'].append('Accessibility pattern detected')
            for team in all_teams:
                team_name = team.name.lower()
                if ('accessibility' in team_name or 
                    'a11y' in team_name or
                    ('practical law' in team_name and 'accessibility' in team_name)):
                    group_teams.append(team.name)
                    debug_info['detection_logic'].append(f'Found accessibility team: {team.name}')
        
        # Test Practical Law detection
        elif 'practical law' in selected_team_name.lower():
            debug_info['detection_logic'].append('Practical Law pattern detected')
            if ' - ' in selected_team_name:
                potential_group = selected_team_name.split(' - ')[-1]
                debug_info['detection_logic'].append(f'Extracted group: {potential_group}')
                for team in all_teams:
                    team_name = team.name.lower()
                    if (potential_group in team_name or 
                        team_name in potential_group or
                        any(keyword in team_name for keyword in potential_group.split())):
                        group_teams.append(team.name)
                        debug_info['detection_logic'].append(f'Found group team: {team.name}')
        
        debug_info['group_teams'] = group_teams
        debug_info['group_teams_count'] = len(group_teams)
        
        return jsonify(debug_info)
        
    except Exception as e:
        logger.error(f"Error in debug team detection: {e}")
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
                from src.ado.ado_access import AzureDevOpsClient
                
                global ado_client
                ado_client = AzureDevOpsClient(
                    ado_data.get('org_url'),
                    ado_data.get('pat')
                )
                app.config['ado_client'] = ado_client
                
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
                    # Update session config
                    session_config['azure_devops'].update(ado_data)
                    session_config['azure_devops']['connected'] = True
                    # Ensure project is set
                    if 'project' not in ado_data or not ado_data.get('project'):
                        # Try to load project from config file
                        load_config_from_file()
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
                from src.openarena.websocket_client import OpenArenaWebSocketClient
                
                # Update environment variables
                if 'esso_token' in oa_data:
                    os.environ['OPENARENA_ESSO_TOKEN'] = oa_data['esso_token']
                if 'websocket_url' in oa_data:
                    os.environ['OPENARENA_WEBSOCKET_URL'] = oa_data['websocket_url']
                if 'workflow_id' in oa_data:
                    os.environ['OPENARENA_GPT5_WORKFLOW_ID'] = oa_data['workflow_id']
                
                global openarena_client
                openarena_client = OpenArenaWebSocketClient()
                app.config['openarena_client'] = openarena_client
                
                results['connections']['openarena'] = {
                    'success': True,
                    'message': 'Connected successfully'
                }
                
                # Update session config
                session_config['openarena'].update(oa_data)
                session_config['openarena']['connected'] = True
                
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

def process_llm_response(llm_response, selected_work_item, all_work_items, hierarchy):
    """Process LLM response using the advanced parser for accurate data extraction."""
    
    try:
        # Check if response is empty or invalid
        if not llm_response or len(llm_response.strip()) < 50:
            logger.warning("LLM response is empty or too short, using fallback parser")
            return process_llm_response_fallback(llm_response, selected_work_item, all_work_items, hierarchy)
        
        # Import the advanced parser
        from llm_response_parser import AdvancedLLMResponseParser, convert_parsed_analysis_to_dict
        
        # Create parser instance
        parser = AdvancedLLMResponseParser()
        
        # Parse the LLM response
        logger.info(f"Starting LLM response parsing with {len(all_work_items)} work items")
        parsed_analysis = parser.parse_response(llm_response, all_work_items, selected_work_item)
        logger.info(f"LLM response parsing completed successfully")
        
        # Convert to the expected format with raw analysis text
        logger.info("Starting conversion to dictionary format")
        analysis_data = convert_parsed_analysis_to_dict(parsed_analysis, llm_response)
        logger.info("Conversion to dictionary format completed successfully")
        
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
            'assignedTo': selected_work_item.fields.get('System.AssignedTo', {}).get('displayName', 'Unassigned') if isinstance(selected_work_item.fields.get('System.AssignedTo'), dict) else str(selected_work_item.fields.get('System.AssignedTo', 'Unassigned')),
            'areaPath': selected_work_item.fields.get('System.AreaPath', ''),
            'iterationPath': selected_work_item.fields.get('System.IterationPath', ''),
            'description': selected_work_item.fields.get('System.Description', ''),
            'reason': selected_work_item.fields.get('System.Reason', '')
        }
        
        # Format hierarchy
        hierarchy_data = []
        if hierarchy and isinstance(hierarchy, dict):
            for level, items in hierarchy.items():
                if isinstance(items, list):
                    for item in items:
                        # Handle both WorkItem objects and dictionaries
                        if hasattr(item, 'fields'):
                            # WorkItem object
                            hierarchy_data.append({
                                'level': level,
                                'id': getattr(item, 'id', ''),
                                'title': item.fields.get('System.Title', ''),
                                'type': item.fields.get('System.WorkItemType', ''),
                                'state': item.fields.get('System.State', '')
                            })
                        else:
                            # Dictionary
                            hierarchy_data.append({
                                'level': level,
                                'id': item.get('id', ''),
                                'title': item.get('title', ''),
                                'type': item.get('type', ''),
                                'state': item.get('state', '')
                            })
        
        # Generate analysis insights with the extracted sections
        from app import generate_analysis_insights
        logger.info(f"Generating analysis insights with {len(all_related_items)} related items")
        insights = generate_analysis_insights(
            all_related_items, 
            selected_work_item_data, 
            analysis_data.get('relationshipPatterns', []), 
            analysis_data.get('riskAssessment', []), 
            analysis_data.get('recommendations', [])
        )
        logger.info(f"Generated insights: {insights}")
        
        # Format confidence breakdown
        confidence_breakdown = {
            'high': len(analysis_data['highConfidenceItems']),
            'medium': len(analysis_data['mediumConfidenceItems']),
            'low': len(analysis_data['lowConfidenceItems'])
        }
        
        return {
            'selectedWorkItem': selected_work_item_data,
            'hierarchy': hierarchy_data,
            'relatedWorkItems': all_related_items,
            'analysisInsights': insights,
            'confidenceBreakdown': confidence_breakdown
            # costInfo will be added by the calling function with actual values
        }
        
    except Exception as e:
        logger.error(f"Error in advanced LLM response parsing: {e}")
        return process_llm_response_fallback(llm_response, selected_work_item, all_work_items, hierarchy)

def process_llm_response_fallback(llm_response, selected_work_item, all_work_items, hierarchy):
    """Fallback LLM response parser using the original simple approach."""
    
    # Handle empty or invalid response
    if not llm_response or len(llm_response.strip()) < 10:
        logger.warning("LLM response is empty, generating mock analysis")
        # Generate a basic mock analysis with some of the related work items
        related_work_items = []
        for i, item in enumerate(all_work_items[:5]):  # Take first 5 items
            if hasattr(item, 'id') and item.id != selected_work_item.id:
                confidence = 'high' if i < 2 else 'medium' if i < 4 else 'low'
                related_work_items.append({
                    'id': item.id,
                    'title': item.fields.get('System.Title', 'No Title') if hasattr(item, 'fields') else 'No Title',
                    'type': item.fields.get('System.WorkItemType', 'Unknown') if hasattr(item, 'fields') else 'Unknown',
                    'state': item.fields.get('System.State', 'Unknown') if hasattr(item, 'fields') else 'Unknown',
                    'assignedTo': item.fields.get('System.AssignedTo', {}).get('displayName', 'Unassigned') if hasattr(item, 'fields') and isinstance(item.fields.get('System.AssignedTo'), dict) else 'Unassigned',
                    'areaPath': item.fields.get('System.AreaPath', '') if hasattr(item, 'fields') else '',
                    'iterationPath': item.fields.get('System.IterationPath', '') if hasattr(item, 'fields') else '',
                    'description': item.fields.get('System.Description', '') if hasattr(item, 'fields') else '',
                    'confidence': confidence,
                    'relationshipType': 'related',
                    'reasoning': 'Identified through automated analysis',
                    'lastUpdated': 'Recently'
                })
        
        # Generate proper analysis insights
        from app import generate_analysis_insights
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
        
        insights = generate_analysis_insights(
            related_work_items, 
            selected_work_item_data, 
            ['Mock analysis - LLM response unavailable'], 
            ['Unable to perform detailed risk assessment'], 
            ['Review related work items manually']
        )
        
        # Return mock analysis
        return {
            'selectedWorkItem': selected_work_item_data,
            'hierarchy': [],
            'relatedWorkItems': related_work_items,
            'analysisInsights': insights,
            'confidenceBreakdown': {
                'high': len([item for item in related_work_items if item['confidence'] == 'high']),
                'medium': len([item for item in related_work_items if item['confidence'] == 'medium']),
                'low': len([item for item in related_work_items if item['confidence'] == 'low'])
            }
            # costInfo will be added by the calling function with actual values
        }
    
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
            # Other analysis sections - don't change confidence
            continue
        
        # Look for work item references in the response
        if '#' in line and any(char.isdigit() for char in line):
            # Extract work item ID
            import re
            work_item_ids = re.findall(r'#(\d+)', line)
            
            for work_item_id in work_item_ids:
                work_item_id = int(work_item_id)
                
                # Find the work item in all_work_items
                related_item = next((item for item in all_work_items if item.id == work_item_id), None)
                
                if related_item and related_item.id != selected_work_item.id:
                    # Determine confidence score based on context
                    confidence = determine_confidence_score(line, related_item, selected_work_item)
                    
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
        
        # Collect analysis insights
        elif current_section == 'patterns' and line and not line.startswith('#'):
            relationship_patterns.append(line)
        elif current_section == 'risk' and line and not line.startswith('#'):
            risk_assessment.append(line)
        elif current_section == 'recommendations' and line and not line.startswith('#'):
            recommendations.append(line)
    
    # Remove duplicates
    seen_ids = set()
    unique_related_items = []
    for item in related_work_items:
        if item['id'] not in seen_ids:
            seen_ids.add(item['id'])
            unique_related_items.append(item)
    
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
        for level, items in hierarchy.items():
            if isinstance(items, list):
                for item in items:
                    hierarchy_data.append({
                        'level': level,
                        'id': item.get('id', ''),
                        'title': item.get('title', ''),
                        'type': item.get('type', ''),
                        'state': item.get('state', '')
                    })
    
    # Format insights
    insights = {
        'patterns': relationship_patterns,
        'risks': risk_assessment,
        'recommendations': recommendations
    }
    
    # Calculate confidence breakdown
    high_count = len([item for item in unique_related_items if item['confidence'] == 'high'])
    medium_count = len([item for item in unique_related_items if item['confidence'] == 'medium'])
    low_count = len([item for item in unique_related_items if item['confidence'] == 'low'])
    
    confidence_breakdown = {
        'high': high_count,
        'medium': medium_count,
        'low': low_count
    }
    
    return {
        'selectedWorkItem': selected_work_item_data,
        'hierarchy': hierarchy_data,
        'relatedWorkItems': unique_related_items,
        'analysisInsights': insights,
        'confidenceBreakdown': confidence_breakdown,
        'costInfo': {
            'cost': 0.0234,  # Mock cost
            'tokens': 1250,  # Mock tokens
            'model': 'gpt-4',
            'timestamp': datetime.now().isoformat()
        }
    }

def determine_confidence_score(line, related_item, selected_work_item):
    """Determine confidence score based on context."""
    line_lower = line.lower()
    
    if 'high confidence' in line_lower or 'strong' in line_lower or 'direct' in line_lower:
        return 'high'
    elif 'medium confidence' in line_lower or 'moderate' in line_lower:
        return 'medium'
    else:
        return 'low'

def determine_relationship_type(line, related_item, selected_work_item):
    """Determine relationship type based on context."""
    line_lower = line.lower()
    
    if 'dependency' in line_lower:
        return 'dependency'
    elif 'similar' in line_lower or 'related' in line_lower:
        return 'similar'
    elif 'blocking' in line_lower or 'blocked' in line_lower:
        return 'blocking'
    else:
        return 'related'

def extract_reasoning(line, related_item, selected_work_item):
    """Extract reasoning from the line."""
    # Simple extraction - in production, you'd want more sophisticated parsing
    if ':' in line:
        return line.split(':', 1)[1].strip()
    else:
        return line.strip()


if __name__ == '__main__':
    try:
        initialize_clients()
        app.run(debug=True, host='0.0.0.0', port=5001)  # Different port to avoid conflicts
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        sys.exit(1)

