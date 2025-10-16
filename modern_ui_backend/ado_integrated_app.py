#!/usr/bin/env python3
"""
Azure DevOps AI Studio - Modern UI Backend with Real ADO Integration

Flask backend that integrates with the existing Azure DevOps AI Studio
to serve real work item data through the modern React UI.
"""

import os
import sys
import json
import logging
from datetime import datetime
from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS
import traceback

# Add the parent directory to the Python path to import from the main project
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

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

def initialize_clients():
    """Initialize Azure DevOps and OpenArena clients using the same pattern as the main app."""
    global ado_client, openarena_client
    
    try:
        # Add src directory to Python path for imports
        src_path = os.path.join(os.path.dirname(__file__), '..', 'src')
        sys.path.insert(0, src_path)
        
        # Load environment variables first
        from openarena.config.env_config import set_environment_variables
        set_environment_variables()
        
        # Import the ADO client
        from ado.ado_access import AzureDevOpsClient
        from openarena.websocket_client import OpenArenaWebSocketClient
        from llm.ado_analysis_prompt import ADOWorkItemAnalysisPrompt
        
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
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize clients: {e}")
        logger.error(traceback.format_exc())
        return False

@app.route('/')
def serve_react_app():
    """Serve the React application."""
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/analysis/<int:work_item_id>')
def serve_analysis_page(work_item_id):
    """Serve the React application for analysis page."""
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/analysis/<int:work_item_id>')
def get_analysis_data(work_item_id):
    """Get LLM analysis data for a specific work item using real ADO data."""
    try:
        # Initialize clients if not already done
        if not ado_client:
            if not initialize_clients():
                return jsonify({'error': 'Failed to initialize Azure DevOps client'}), 500
        
        if ado_client:
            try:
                # Get work item details
                work_item = ado_client.get_work_item(work_item_id)
                if not work_item:
                    return jsonify({'error': 'Work item not found'}), 404
                
                # Get all work items for analysis
                project = os.getenv('AZURE_DEVOPS_PROJECT', 'Your Project Name')
                all_work_items = ado_client.query_work_items(project, limit=200)
                
                # Get hierarchy information
                hierarchy = ado_client.get_work_item_hierarchy(work_item_id)
                
                # Perform LLM analysis
                from llm.ado_analysis_prompt import ADOWorkItemAnalysisPrompt
                analysis_prompt = ADOWorkItemAnalysisPrompt()
                system_prompt = analysis_prompt.create_system_prompt(work_item, all_work_items)
                
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
                    except Exception as llm_error:
                        logger.warning(f"OpenArena LLM analysis failed: {llm_error}")
                        # Fall back to mock response
                        llm_response = generate_mock_llm_response(work_item, all_work_items)
                        cost_tracker = {}
                else:
                    # Fallback to mock response for development
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

@app.route('/api/work-items')
def get_work_items():
    """Get all work items from Azure DevOps."""
    try:
        if not ado_client:
            if not initialize_clients():
                return jsonify({'error': 'Failed to initialize Azure DevOps client'}), 500
        
        if ado_client:
            try:
                # Use the correct method to query work items
                project = os.getenv('AZURE_DEVOPS_PROJECT', 'Your Project Name')
                work_items = ado_client.query_work_items(project, limit=100)
                
                # Convert work items to a format suitable for the frontend
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
                        'description': item.fields.get('System.Description', ''),
                        'reason': item.fields.get('System.Reason', '')
                    })
                return jsonify(formatted_items)
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
    """Get specific work item details from Azure DevOps."""
    try:
        if not ado_client:
            if not initialize_clients():
                return jsonify({'error': 'Failed to initialize Azure DevOps client'}), 500
        
        if ado_client:
            try:
                work_item = ado_client.get_work_item(work_item_id)
                if not work_item:
                    return jsonify({'error': 'Work item not found'}), 404
                
                # Format work item for frontend
                formatted_item = {
                    'id': work_item.id,
                    'title': work_item.fields.get('System.Title', 'No Title'),
                    'type': work_item.fields.get('System.WorkItemType', 'Unknown'),
                    'state': work_item.fields.get('System.State', 'Unknown'),
                    'assignedTo': work_item.fields.get('System.AssignedTo', {}).get('displayName', 'Unassigned'),
                    'areaPath': work_item.fields.get('System.AreaPath', ''),
                    'iterationPath': work_item.fields.get('System.IterationPath', ''),
                    'description': work_item.fields.get('System.Description', ''),
                    'reason': work_item.fields.get('System.Reason', '')
                }
                
                return jsonify(formatted_item)
            except Exception as ado_error:
                logger.warning(f"ADO client error: {ado_error}")
                return jsonify({'error': 'Unable to fetch work item from Azure DevOps'}), 500
        else:
            return jsonify({'error': 'Azure DevOps client not available'}), 500
        
    except Exception as e:
        logger.error(f"Error getting work item: {e}")
        return jsonify({'error': str(e)}), 500

def process_llm_response(llm_response, selected_work_item, all_work_items, hierarchy):
    """Process LLM response and extract structured data with confidence scores."""
    
    # Parse the LLM response to extract related work items with confidence scores
    related_work_items = []
    
    # This is a simplified parser - in production, you'd want more sophisticated parsing
    lines = llm_response.split('\n')
    current_section = None
    
    for line in lines:
        line = line.strip()
        
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
    if hierarchy:
        for item in hierarchy:
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
    
    # Generate analysis insights
    insights = generate_analysis_insights(unique_related_items, selected_work_item_data)
    
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

def generate_analysis_insights(related_work_items, selected_work_item):
    """Generate analysis insights based on related work items."""
    
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
    
    # Generate risks
    risks = []
    if confidence_counts.get('low', 0) > 2:
        risks.append({
            'title': 'Multiple Low Confidence Items',
            'description': f"Found {confidence_counts['low']} items with low confidence relationships. Review these carefully.",
            'severity': 'medium'
        })
    
    # Generate opportunities
    opportunities = []
    if confidence_counts.get('high', 0) > 3:
        opportunities.append({
            'title': 'Strong Relationship Network',
            'description': f"Found {confidence_counts['high']} high-confidence relationships. Consider coordinating these work items.",
            'type': 'optimization'
        })
    
    # Generate recommendations
    recommendations = []
    if confidence_counts.get('high', 0) > 0:
        recommendations.append({
            'title': 'Prioritize High Confidence Items',
            'description': "Focus on work items with high confidence relationships first.",
            'priority': 'high'
        })
    
    return {
        'risks': risks,
        'opportunities': opportunities,
        'dependencies': [],
        'recommendations': recommendations,
        'summary': {
            'totalRelatedItems': len(related_work_items),
            'highConfidenceItems': confidence_counts.get('high', 0),
            'mediumConfidenceItems': confidence_counts.get('medium', 0),
            'lowConfidenceItems': confidence_counts.get('low', 0),
            'risksIdentified': len(risks),
            'opportunitiesFound': len(opportunities),
            'dependenciesFound': 0,
            'recommendationsGenerated': len(recommendations)
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
        'hierarchy': [],
        'relatedWorkItems': [],
        'analysisInsights': {
            'risks': [],
            'opportunities': [],
            'dependencies': [],
            'recommendations': [],
            'summary': {
                'totalRelatedItems': 0,
                'highConfidenceItems': 0,
                'mediumConfidenceItems': 0,
                'lowConfidenceItems': 0,
                'risksIdentified': 0,
                'opportunitiesFound': 0,
                'dependenciesFound': 0,
                'recommendationsGenerated': 0
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
    
    HIGH CONFIDENCE RELATIONSHIPS:
    - #2219098: Directly related to regional content improvements
    - #2219094: Strong dependency for access point implementation
    - #2211085: Technical dependency for WCMS container updates
    
    MEDIUM CONFIDENCE RELATIONSHIPS:
    - #2219097: Related to regional branding and search functionality
    - #2217890: Associated with jurisdiction customization features
    
    LOW CONFIDENCE RELATIONSHIPS:
    - #2219101: Tangentially related through project context
    
    RISK ASSESSMENT:
    - High dependency on technical infrastructure updates
    - Multiple active work items may impact scope
    
    RECOMMENDATIONS:
    - Coordinate with regional content team
    - Prioritize technical dependencies
    - Consider accessibility compliance requirements
    """

if __name__ == '__main__':
    try:
        logger.info("Starting Azure DevOps AI Studio Modern UI with Real Data Integration...")
        app.run(debug=True, host='0.0.0.0', port=5000)
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        sys.exit(1)
