"""
Azure DevOps Board Access Script

This script demonstrates how to access Azure DevOps boards using the Azure DevOps Python SDK.
It includes examples for authentication, accessing work items, querying boards, and manipulating ADO data.

Prerequisites:
- Python 3.6 or higher
- Azure DevOps account with appropriate permissions
- Personal Access Token (PAT) for authentication

Installation:
pip install azure-devops
"""

from azure.devops.connection import Connection
from msrest.authentication import BasicAuthentication
import os
import argparse
import logging
import threading
import time
from datetime import datetime
import json
import os
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/ado_access.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AzureDevOpsClient:
    """Client for interacting with Azure DevOps."""
    
    def __init__(self, organization_url, personal_access_token):
        """
        Initialize the Azure DevOps client.
        
        Args:
            organization_url (str): The URL of your Azure DevOps organization.
            personal_access_token (str): Your Personal Access Token for authentication.
        """
        self.organization_url = organization_url
        self.personal_access_token = personal_access_token
        
        # Create a connection to Azure DevOps
        credentials = BasicAuthentication('', personal_access_token)
        self.connection = Connection(base_url=organization_url, creds=credentials)
        
        # Initialize clients
        self.work_item_client = self.connection.clients.get_work_item_tracking_client()
        self.work_client = self.connection.clients.get_work_client()
        self.git_client = self.connection.clients.get_git_client()
        self.build_client = self.connection.clients.get_build_client()
        
        # Create session for REST API calls
        import requests
        self.session = requests.Session()
        
        # Configure timeouts and performance settings
        self.session.timeout = (10, 60)  # (connect_timeout, read_timeout) - Keep reasonable for server-side 30s limit
        
        # Configure connection pooling and retries for better performance
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        # Configure connection pooling
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=20
        )
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Try using the Azure DevOps SDK's authentication method
        try:
            # Get the authentication from the connection
            auth_header = self.connection._credentials.authentication_header
            if auth_header:
                self.session.headers.update({
                    'Authorization': auth_header,
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                })
            else:
                # Fallback to Basic Auth
                self.session.auth = ('', personal_access_token)
                self.session.headers.update({
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                })
        except Exception as e:
            logger.warning(f"Could not get SDK auth header: {e}, using Basic Auth")
            # Fallback to Basic Auth
            self.session.auth = ('', personal_access_token)
            self.session.headers.update({
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            })
        
        logger.info(f"Connected to Azure DevOps organization: {organization_url}")
        
        # Load team area paths configuration
        self.team_area_paths_config = self._load_team_area_paths_config()
    
    def _load_team_area_paths_config(self):
        """Load team area paths configuration from JSON file."""
        try:
            config_path = Path(__file__).parent.parent.parent / "config" / "team_area_paths.json"
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
                logger.info("Loaded team area paths configuration")
                return config
            else:
                logger.warning(f"Team area paths configuration not found at {config_path}")
                return {}
        except Exception as e:
            logger.error(f"Error loading team area paths configuration: {e}")
            return {}
    
    def _get_team_area_paths(self, team_name, project):
        """Get area paths for a team using configuration or fallback to default construction."""
        if not self.team_area_paths_config:
            # Fallback to simple construction
            return f"{project}\\{team_name}"
        
        # Look for team in configuration
        team_mappings = self.team_area_paths_config.get('team_area_path_mappings', {})
        
        # Try exact match first
        if team_name in team_mappings:
            area_paths = team_mappings[team_name]
            if area_paths and len(area_paths) > 0:
                # Use the first area path from configuration
                return area_paths[0]
        
        # Try partial matching if enabled - use more precise matching
        if self.team_area_paths_config.get('area_path_patterns', {}).get('partial_matching', False):
            # Sort by length (longest first) to prefer more specific matches
            sorted_teams = sorted(team_mappings.items(), key=lambda x: len(x[0]), reverse=True)
            
            for config_team_name, area_paths in sorted_teams:
                # More precise partial matching - check if team name starts with config name
                # This prevents "Practical Law" from matching "Practical Law - Accessibility-Tigers"
                # but allows "Practical Law - Accessibility" to match "Practical Law - Accessibility-Tigers"
                if team_name.lower().startswith(config_team_name.lower()):
                    if area_paths and len(area_paths) > 0:
                        logger.info(f"Found partial match for team '{team_name}' -> '{config_team_name}'")
                        return area_paths[0]
        
        # Fallback to simple construction
        logger.info(f"No configuration found for team '{team_name}', using default construction")
        return f"{project}\\{team_name}"
    
    def get_team_area_paths(self, project, team_id):
        """
        Get area paths for a specific team using the team ID.
        This method tries multiple approaches to get team area paths.
        
        Args:
            project (str): The project name
            team_id (str): The team ID
            
        Returns:
            list: List of area path strings for the team
        """
        try:
            # Approach 1: Try using the Azure DevOps REST API
            try:
                import requests
                import base64
                
                # Construct the API URL
                org_url = self.organization_url.rstrip('/')
                api_url = f"{org_url}/{project}/_apis/teams/{team_id}/areas?api-version=7.1-preview.1"
                
                # Create basic auth header
                credentials = f":{self.personal_access_token}"
                encoded_credentials = base64.b64encode(credentials.encode()).decode()
                headers = {
                    'Authorization': f'Basic {encoded_credentials}',
                    'Content-Type': 'application/json'
                }
                
                logger.info(f"Getting team area paths for team {team_id} in project {project}")
                response = requests.get(api_url, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    area_paths = []
                    if 'value' in data:
                        for area in data['value']:
                            if 'path' in area:
                                area_paths.append(area['path'])
                                logger.info(f"Found team area path: {area['path']}")
                    
                    if area_paths:
                        logger.info(f"Retrieved {len(area_paths)} area paths for team {team_id}")
                        return area_paths
                else:
                    logger.warning(f"REST API approach failed: {response.status_code} - {response.text}")
            except Exception as e:
                logger.warning(f"REST API approach failed: {e}")
            
            # Approach 2: Try using the Azure DevOps SDK (if available)
            try:
                # This is a fallback - the SDK might not have direct team areas support
                # but we can try to get team information and construct area paths
                core_client = self.connection.clients.get_core_client()
                
                # Get team by ID
                teams = core_client.get_teams(project)
                for team in teams:
                    if hasattr(team, 'id') and str(team.id) == str(team_id):
                        # Found the team, try to get area path information
                        if hasattr(team, 'default_area_path') and team.default_area_path:
                            logger.info(f"Found team default area path: {team.default_area_path}")
                            return [team.default_area_path]
                        break
            except Exception as e:
                logger.warning(f"SDK approach failed: {e}")
            
            # Approach 3: Fallback - return empty list (will use constructed path)
            logger.info(f"No specific area paths found for team {team_id}, will use constructed path")
            return []
                
        except Exception as e:
            logger.error(f"Error getting team area paths for team {team_id}: {e}")
            return []

    def _generate_all_teams_wiql_query(self, project, work_item, verified_teams, date_filter='last-month', work_item_types=None):
        """
        Generate WIQL query that searches across all verified teams at once.
        
        Args:
            project (str): The project name
            work_item: The work item object to analyze
            verified_teams (list): List of verified team names
            date_filter (str): Date filter option
            work_item_types (list): List of work item types to include
            
        Returns:
            str: WIQL query string that searches all verified teams
        """
        try:
            # Get work item details
            if hasattr(work_item, 'fields'):
                work_item_title = work_item.fields.get('System.Title', '').strip()
                work_item_type = work_item.fields.get('System.WorkItemType', '')
            elif hasattr(work_item, 'title'):
                work_item_title = work_item.title.strip()
                work_item_type = getattr(work_item, 'workItemType', '')
            elif isinstance(work_item, dict):
                work_item_title = work_item.get('title', '').strip()
                work_item_type = work_item.get('workItemType', '')
            else:
                logger.error(f"Unknown work item structure: {type(work_item)}")
                return None
            
            if not work_item_title or len(work_item_title) < 5:
                return None
            
            # Generate intelligent phrase combinations from the title
            title_phrases = self._generate_title_phrase_combinations(work_item_title)
            
            if not title_phrases:
                return None
            
            # Build CONTAINS clauses for title-based matching
            title_conditions = []
            for phrase in title_phrases:
                escaped_phrase = phrase.replace("'", "''")
                title_conditions.append(f"[System.Title] CONTAINS '{escaped_phrase}'")
            
            title_where_clause = " OR ".join(title_conditions)
            
            # Build the complete WIQL query
            wiql_query = f"""
            SELECT [System.Id], [System.Title], [System.WorkItemType], [System.State],
                   [System.AssignedTo], [System.CreatedBy], [System.CreatedDate], [System.Description],
                   [System.AreaPath], [System.TeamProject]
            FROM WorkItems
            WHERE [System.TeamProject] = '{project}'
            AND [System.Id] != {work_item.id}
            AND [System.State] <> 'Removed'
            AND ({title_where_clause})"""
            
            # Add work item type filter
            if work_item_types and len(work_item_types) > 0:
                # Escape work item types for WIQL
                escaped_types = [t.replace("'", "''") for t in work_item_types]
                type_conditions = " OR ".join([f"[System.WorkItemType] = '{t}'" for t in escaped_types])
                wiql_query += f"\n            AND ({type_conditions})"
            elif work_item_type:
                # Fallback to original work item type if no specific types provided
                wiql_query += f"\n            AND ([System.WorkItemType] = '{work_item_type}' OR [System.WorkItemType] = 'User Story' OR [System.WorkItemType] = 'Task')"
            
            # Add date filter based on selection
            date_condition = self._get_date_filter_condition(date_filter)
            if date_condition:
                wiql_query += f"\n            AND {date_condition}"
            else:
                # Fallback to 180 days if no valid date filter
                wiql_query += f"\n            AND [System.CreatedDate] >= @Today - 180"
            
            # Build area path filter for all verified teams using the mapping file
            area_conditions = []
            
            # Load team area path mappings
            try:
                import json
                import os
                mapping_file = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'team_area_paths.json')
                if os.path.exists(mapping_file):
                    with open(mapping_file, 'r', encoding='utf-8') as f:
                        mapping_data = json.load(f)
                        mappings = mapping_data.get('mappings', {})
                        
                        for team_name in verified_teams:
                            if team_name in mappings:
                                team_data = mappings[team_name]
                                if team_data.get('verified', False):
                                    area_path = team_data.get('area_path', '')
                                    if area_path:
                                        escaped_area_path = area_path.replace("'", "''")
                                        area_conditions.append(f"[System.AreaPath] UNDER '{escaped_area_path}'")
                                    else:
                                        logger.warning(f"No area path found for verified team {team_name}")
                                else:
                                    logger.warning(f"Team {team_name} is not verified in mapping file")
                            else:
                                logger.warning(f"Team {team_name} not found in mapping file")
                else:
                    logger.warning(f"Mapping file not found: {mapping_file}")
                    # Fallback to old logic if mapping file doesn't exist
                    for team_name in verified_teams:
                        team_name_escaped = team_name.replace("'", "''")
                        area_conditions.append(f"[System.AreaPath] UNDER '{project}\\{team_name_escaped}'")
            except Exception as e:
                logger.error(f"Error loading team area path mappings: {e}")
                # Fallback to old logic if there's an error
                for team_name in verified_teams:
                    team_name_escaped = team_name.replace("'", "''")
                    area_conditions.append(f"[System.AreaPath] UNDER '{project}\\{team_name_escaped}'")
            
            # Add area path filter for all teams
            if area_conditions:
                wiql_query += f"\n            AND ({' OR '.join(area_conditions)})"
                logger.info(f"Using area path filters for {len(verified_teams)} verified teams: {len(area_conditions)} area paths")
            
            # Order by creation date descending
            wiql_query += "\n            ORDER BY [System.CreatedDate] DESC"
            
            # Print the complete WIQL query for debugging (only for first period)
            if date_filter == 'last-6-months':
                logger.info(f"GENERATED WIQL QUERY ({date_filter}):")
                logger.info("=" * 80)
                logger.info(wiql_query)
                logger.info("=" * 80)
            
            return wiql_query
            
        except Exception as e:
            logger.error(f"Error generating all-teams WIQL query: {e}")
            return None

    def _generate_team_based_wiql_query(self, project, work_item, team_name, team_info=None, date_filter='last-month', work_item_types=None):
        """
        Generate WIQL query using team context with proper area path resolution and additional filters.
        
        Args:
            project (str): The project name
            work_item: The work item object to analyze
            team_name (str): The actual team name from Azure DevOps
            team_info: Team information from Azure DevOps API (should include team ID)
            date_filter (str): Date filter option
            work_item_types (list): List of work item types to include
            
        Returns:
            str: WIQL query string using team context
        """
        try:
            # Get work item details
            if hasattr(work_item, 'fields'):
                work_item_title = work_item.fields.get('System.Title', '').strip()
                work_item_type = work_item.fields.get('System.WorkItemType', '')
            elif hasattr(work_item, 'title'):
                work_item_title = work_item.title.strip()
                work_item_type = getattr(work_item, 'workItemType', '')
            elif isinstance(work_item, dict):
                work_item_title = work_item.get('title', '').strip()
                work_item_type = work_item.get('workItemType', '')
            else:
                logger.error(f"Unknown work item structure: {type(work_item)}")
                return None
            
            if not work_item_title or len(work_item_title) < 5:
                return None
            
            # Generate intelligent phrase combinations from the title
            title_phrases = self._generate_title_phrase_combinations(work_item_title)
            
            if not title_phrases:
                return None
            
            # Build CONTAINS clauses for title-based matching
            title_conditions = []
            for phrase in title_phrases:
                escaped_phrase = phrase.replace("'", "''")
                title_conditions.append(f"[System.Title] CONTAINS '{escaped_phrase}'")
            
            title_where_clause = " OR ".join(title_conditions)
            
            # Build the complete WIQL query with team context
            wiql_query = f"""
            SELECT [System.Id], [System.Title], [System.WorkItemType], [System.State],
                   [System.AssignedTo], [System.CreatedBy], [System.CreatedDate], [System.Description],
                   [System.AreaPath], [System.TeamProject]
            FROM WorkItems
            WHERE [System.TeamProject] = '{project}'
            AND [System.Id] != {work_item.id}
            AND [System.State] <> 'Removed'
            AND ({title_where_clause})"""
            
            # Add work item type filter
            if work_item_types and len(work_item_types) > 0:
                # Escape work item types for WIQL
                escaped_types = [t.replace("'", "''") for t in work_item_types]
                type_conditions = " OR ".join([f"[System.WorkItemType] = '{t}'" for t in escaped_types])
                wiql_query += f"\n            AND ({type_conditions})"
            elif work_item_type:
                # Fallback to original work item type if no specific types provided
                wiql_query += f"\n            AND ([System.WorkItemType] = '{work_item_type}' OR [System.WorkItemType] = 'User Story' OR [System.WorkItemType] = 'Task')"
            
            # Add date filter based on selection
            date_condition = self._get_date_filter_condition(date_filter)
            if date_condition:
                wiql_query += f"\n            AND {date_condition}"
            else:
                # Fallback to 180 days if no valid date filter
                wiql_query += f"\n            AND [System.CreatedDate] >= @Today - 180"
            
            # Use team context with proper area path resolution
            team_area_paths = []
            
            # Option 1: Get area paths using team ID (recommended approach)
            if team_info and hasattr(team_info, 'id') and team_info.id:
                logger.info(f"Getting area paths for team ID: {team_info.id}")
                team_area_paths = self.get_team_area_paths(project, team_info.id)
            
            # Option 2: Fallback to default area path if available
            if not team_area_paths and team_info and hasattr(team_info, 'default_area_path') and team_info.default_area_path:
                team_area_paths = [team_info.default_area_path]
                logger.info(f"Using team default area path: {team_info.default_area_path}")
            
            # Option 3: Fallback to constructed area path
            if not team_area_paths:
                team_name_escaped = team_name.replace("'", "''")
                team_area_paths = [f"{project}\\{team_name_escaped}"]
                logger.info(f"Using constructed team area path: {project}\\{team_name_escaped}")
            
            # Build area path filter using UNDER operator
            if team_area_paths:
                area_conditions = []
                for area_path in team_area_paths:
                    escaped_area_path = area_path.replace("'", "''")
                    area_conditions.append(f"[System.AreaPath] UNDER '{escaped_area_path}'")
                
                if area_conditions:
                    if len(area_conditions) == 1:
                        wiql_query += f"\n            AND {area_conditions[0]}"
                    else:
                        wiql_query += f"\n            AND ({' OR '.join(area_conditions)})"
                    
                    logger.info(f"Using team area path filters: {area_conditions}")
            
            # Order by creation date descending
            wiql_query += "\n            ORDER BY [System.CreatedDate] DESC"
            
            return wiql_query
            
        except Exception as e:
            logger.error(f"Error generating team-based WIQL query: {str(e)}")
            return None

    def _get_date_filter_condition(self, date_filter):
        """
        Get WIQL date condition based on the selected date filter.
        
        Args:
            date_filter (str): The date filter option
            
        Returns:
            str: WIQL date condition string
        """
        try:
            from datetime import datetime, timedelta
            
            if date_filter == 'current-iteration':
                return "[System.CreatedDate] >= @CurrentIteration"
            elif date_filter == 'previous-iteration':
                return "[System.CreatedDate] >= @PreviousIteration"
            elif date_filter == 'last-2-iterations':
                return "[System.CreatedDate] >= @PreviousIteration"
            elif date_filter == 'last-month':
                return "[System.CreatedDate] >= @Today - 1095"
            elif date_filter == 'last-6-months':
                return "[System.CreatedDate] >= @Today - 180"
            elif date_filter == '6-12-months':
                return "[System.CreatedDate] >= @Today - 365 AND [System.CreatedDate] < @Today - 180"
            elif date_filter == '12-18-months':
                return "[System.CreatedDate] >= @Today - 540 AND [System.CreatedDate] < @Today - 365"
            elif date_filter == '18-24-months':
                return "[System.CreatedDate] >= @Today - 730 AND [System.CreatedDate] < @Today - 540"
            elif date_filter == '24-30-months':
                return "[System.CreatedDate] >= @Today - 912 AND [System.CreatedDate] < @Today - 730"
            elif date_filter == '30-36-months':
                return "[System.CreatedDate] >= @Today - 1095 AND [System.CreatedDate] < @Today - 912"
            # 3-month intervals for Balanced Search (up to 2 years)
            elif date_filter == 'last-3-months':
                return "[System.CreatedDate] >= @Today - 90"
            elif date_filter == '3-6-months':
                return "[System.CreatedDate] >= @Today - 180 AND [System.CreatedDate] < @Today - 90"
            elif date_filter == '6-9-months':
                return "[System.CreatedDate] >= @Today - 270 AND [System.CreatedDate] < @Today - 180"
            elif date_filter == '9-12-months':
                return "[System.CreatedDate] >= @Today - 365 AND [System.CreatedDate] < @Today - 270"
            elif date_filter == '12-15-months':
                return "[System.CreatedDate] >= @Today - 450 AND [System.CreatedDate] < @Today - 365"
            elif date_filter == '15-18-months':
                return "[System.CreatedDate] >= @Today - 540 AND [System.CreatedDate] < @Today - 450"
            elif date_filter == '18-21-months':
                return "[System.CreatedDate] >= @Today - 630 AND [System.CreatedDate] < @Today - 540"
            elif date_filter == '21-24-months':
                return "[System.CreatedDate] >= @Today - 730 AND [System.CreatedDate] < @Today - 630"
            elif date_filter == 'last-2-months':
                return "[System.CreatedDate] >= @Today - 60"
            elif date_filter == 'current-quarter':
                # Approximate current quarter (3 months)
                return "[System.CreatedDate] >= @Today - 90"
            elif date_filter == 'previous-quarter':
                # Approximate previous quarter (3-6 months ago)
                return "[System.CreatedDate] >= @Today - 180 AND [System.CreatedDate] < @Today - 90"
            elif date_filter == 'last-3-quarters':
                # Approximate last 3 quarters (9 months)
                return "[System.CreatedDate] >= @Today - 270"
            elif date_filter == '1-year':
                return "[System.CreatedDate] >= @Today - 365"
            elif date_filter == '2-years':
                return "[System.CreatedDate] >= @Today - 730"
            elif date_filter == '3-years':
                return "[System.CreatedDate] >= @Today - 1095"
            elif date_filter == '4-years':
                return "[System.CreatedDate] >= @Today - 1460"
            elif date_filter == '5-years':
                return "[System.CreatedDate] >= @Today - 1825"
            else:
                # Default to last 3 years
                return "[System.CreatedDate] >= @Today - 1095"
                
        except Exception as e:
            logger.error(f"Error generating date filter condition: {e}")
            return "[System.CreatedDate] >= @Today - 1095"  # Fallback to last 3 years

    def _execute_scope_based_search(self, project, work_item, teams_to_search, max_results_per_team=10, date_filter='last-month', work_item_types=None):
        """
        Execute search across multiple teams based on scope with time-based batching.
        Waits for all time periods to complete before returning consolidated results.
        
        Args:
            project (str): The project name
            work_item: The work item to find related items for
            teams_to_search (list): List of team names to search
            max_results_per_team (int): Maximum results per team (now used as total limit)
            date_filter (str): Date filter option
            work_item_types (list): List of work item types to include
            
        Returns:
            list: List of work item references
        """
        try:
            all_results = []
            seen_ids = set()
            
            # Define time periods for batching (6 months each, up to 3 years)
            time_periods = [
                ("last-6-months", "Last 6 months"),
                ("6-12-months", "6-12 months ago"), 
                ("12-18-months", "12-18 months ago"),
                ("18-24-months", "18-24 months ago"),
                ("24-30-months", "24-30 months ago"),
                ("30-36-months", "30-36 months ago")
            ]
            
            # Search all time periods sequentially and wait for completion
            logger.info("Starting comprehensive 3-year search across all time periods...")
            
            for i, (period_name, period_desc) in enumerate(time_periods):
                logger.info(f"Processing {period_desc}")
                # Only print WIQL query for the first period (last-6-months)
                period_results = self._search_time_period(project, work_item, teams_to_search, period_name, work_item_types, print_query=(i == 0))
                
                if period_results:
                    new_items = []
                    for item in period_results:
                        if item.id not in seen_ids:
                            all_results.append(item)
                            seen_ids.add(item.id)
                            new_items.append(item)
                    logger.info(f"{period_desc}: Found {len(new_items)} new items")
                else:
                    logger.info(f"{period_desc}: No items found")
                
                # Small delay between periods to avoid overwhelming the API
                time.sleep(0.5)
            
            logger.info(f"Comprehensive search completed. Total items found: {len(all_results)}")
            return all_results
            
        except Exception as e:
            logger.error(f"Error in scope-based search: {e}")
            return []
    
    def _execute_balanced_keyword_search(self, project, work_item, teams_to_search, max_results_per_team=10, date_filter='last-month', work_item_types=None):
        """
        Execute keyword-based search for Balanced Search scope.
        Uses individual keyword matching instead of full title phrases.
        
        Args:
            project (str): The project name
            work_item: The work item to find related items for
            teams_to_search (list): List of team names to search
            max_results_per_team (int): Maximum results per team
            date_filter (str): Date filter option
            work_item_types (list): List of work item types to include
            
        Returns:
            list: List of work item references
        """
        try:
            if not work_item or not hasattr(work_item, 'fields'):
                return []
            
            work_item_types = work_item_types or ['Bug', 'User Story', 'Task', 'Feature', 'Epic']
            title = work_item.fields.get('System.Title', '')
            
            if not title:
                return []
            
            # Extract meaningful phrases from title for better semantic matching
            phrases = self._extract_meaningful_phrases(work_item)
            
            if not phrases:
                logger.info("No meaningful phrases found for balanced search")
                return []
            
            logger.info(f"BALANCED SEARCH - Using phrases: {phrases}")
            
            # Build WIQL query with phrase matching
            phrase_conditions = []
            for phrase in phrases:
                escaped_phrase = phrase.replace("'", "''")
                phrase_conditions.append(f"[System.Title] CONTAINS '{escaped_phrase}'")
            
            if not phrase_conditions:
                return []
            
            phrase_where_clause = " OR ".join(phrase_conditions)
            
            # Build area path conditions for selected teams
            area_conditions = []
            try:
                logger.info(f"DEBUG: Looking for area paths for teams: {teams_to_search}")
                import json
                import os
                mapping_file = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'team_area_paths.json')
                logger.info(f"DEBUG: Mapping file path: {mapping_file}")
                if os.path.exists(mapping_file):
                    with open(mapping_file, 'r', encoding='utf-8') as f:
                        mapping_data = json.load(f)
                        mappings = mapping_data.get('mappings', {})
                        logger.info(f"DEBUG: Loaded mappings with {len(mappings)} teams")
                        
                        for team_name in teams_to_search:
                            logger.info(f"DEBUG: Looking for team '{team_name}' in mappings")
                            if team_name in mappings:
                                team_data = mappings[team_name]
                                logger.info(f"DEBUG: Found team data: {team_data}")
                                if team_data.get('verified', False):
                                    area_path = team_data.get('area_path', '')
                                    if area_path:
                                        escaped_area_path = area_path.replace("'", "''")
                                        area_conditions.append(f"[System.AreaPath] UNDER '{escaped_area_path}'")
                                        logger.info(f"DEBUG: Added area path: {area_path}")
                                    else:
                                        logger.warning(f"DEBUG: No area path found for team {team_name}")
                                else:
                                    logger.warning(f"DEBUG: Team {team_name} not verified")
                            else:
                                logger.warning(f"DEBUG: Team '{team_name}' not found in mappings")
                else:
                    logger.error(f"DEBUG: Mapping file not found at {mapping_file}")
            except Exception as e:
                logger.error(f"Error loading team area path mappings: {e}")
                return []
            
            if not area_conditions:
                logger.warning("No valid area paths found for balanced search teams")
                return []
            
            # Build the complete WIQL query
            wiql_query = f"""
            SELECT [System.Id], [System.Title], [System.WorkItemType], [System.State],
                   [System.AssignedTo], [System.CreatedBy], [System.CreatedDate], [System.Description],
                   [System.AreaPath], [System.TeamProject]
            FROM WorkItems
            WHERE [System.TeamProject] = '{project}'
            AND [System.Id] != {work_item.id}
            AND [System.State] <> 'Removed'
            AND ({phrase_where_clause})"""
            
            # Add work item type filter
            if work_item_types and len(work_item_types) > 0:
                escaped_types = [t.replace("'", "''") for t in work_item_types]
                type_conditions = " OR ".join([f"[System.WorkItemType] = '{t}'" for t in escaped_types])
                wiql_query += f"\n            AND ({type_conditions})"
            
            # Add date filter
            date_condition = self._get_date_filter_condition(date_filter)
            if date_condition:
                wiql_query += f"\n            AND {date_condition}"
            else:
                wiql_query += f"\n            AND [System.CreatedDate] >= @Today - 180"
            
            # Add area path filter for selected teams
            wiql_query += f"\n            AND ({' OR '.join(area_conditions)})"
            
            # Order by creation date descending
            wiql_query += "\n            ORDER BY [System.CreatedDate] DESC"
            
            # Print the WIQL query for debugging
            logger.info(f"BALANCED SEARCH WIQL QUERY:")
            logger.info("=" * 80)
            logger.info(wiql_query)
            logger.info("=" * 80)
            
            # Execute the query
            wiql = {"query": wiql_query}
            query_result = self.work_item_client.query_by_wiql(wiql)
            
            if query_result and hasattr(query_result, 'work_items') and query_result.work_items:
                logger.info(f"BALANCED SEARCH - Found {len(query_result.work_items)} items using keyword search")
                return query_result.work_items
            else:
                logger.info("BALANCED SEARCH - No items found using keyword search")
                return []
                
        except Exception as e:
            logger.error(f"Error in balanced keyword search: {e}")
            return []
    
    def _execute_balanced_keyword_search_with_batching(self, project, work_item, teams_to_search, max_results_per_team=20, date_filter='last-month', work_item_types=None):
        """
        Execute keyword-based search for Balanced Search with 3-year batching logic.
        Uses keyword matching (not title phrases) with time-based batching like Laser Focus.
        
        Args:
            project (str): The project name
            work_item: The work item to find related items for
            teams_to_search (list): List of team names to search
            max_results_per_team (int): Maximum results per team
            date_filter (str): Date filter option
            work_item_types (list): List of work item types to include
            
        Returns:
            list: List of work item references
        """
        try:
            all_results = []
            seen_ids = set()
            
            # Define time periods for 2-year batching with 3-month intervals (Balanced Search only)
            time_periods = [
                ('last-3-months', 'Last 3 months'),
                ('3-6-months', '3-6 months ago'),
                ('6-9-months', '6-9 months ago'),
                ('9-12-months', '9-12 months ago'),
                ('12-15-months', '12-15 months ago'),
                ('15-18-months', '15-18 months ago'),
                ('18-21-months', '18-21 months ago'),
                ('21-24-months', '21-24 months ago')
            ]
            
            # Smart fallback strategy: Try 3-word phrases first, fallback to 2-word phrases
            logger.info("Starting comprehensive 2-year keyword search with smart fallback strategy...")
            
            # Determine phrase strategy based on title length
            title = work_item.fields.get('System.Title', '')
            title_words = len(title.split())
            use_3_word_phrases = title_words >= 8  # Use 3-word phrases for lengthy titles
            
            # Track which strategy worked for the first batch
            strategy_used = None
            
            for i, (period_name, period_desc) in enumerate(time_periods):
                logger.info(f"Processing {period_desc}")
                
                # For first batch, try smart fallback strategy
                if i == 0:  # First batch (last-3-months)
                    if use_3_word_phrases:
                        logger.info("BALANCED SEARCH: Trying 3-word consecutive phrases for first batch...")
                        period_results = self._search_time_period_keywords(project, work_item, teams_to_search, period_name, work_item_types, print_query=True, phrase_length=3)
                        
                        if period_results and len(period_results) > 0:
                            strategy_used = 3
                            logger.info(f"BALANCED SEARCH: 3-word phrases successful, found {len(period_results)} items")
                        else:
                            logger.info("BALANCED SEARCH: 3-word phrases returned no results, falling back to 2-word phrases...")
                            period_results = self._search_time_period_keywords(project, work_item, teams_to_search, period_name, work_item_types, print_query=False, phrase_length=2)
                            strategy_used = 2
                            logger.info(f"BALANCED SEARCH: 2-word phrases fallback, found {len(period_results)} items")
                    else:
                        logger.info("BALANCED SEARCH: Using 2-word consecutive phrases for first batch...")
                        period_results = self._search_time_period_keywords(project, work_item, teams_to_search, period_name, work_item_types, print_query=True, phrase_length=2)
                        strategy_used = 2
                else:
                    # For subsequent batches, use the strategy that worked for first batch
                    phrase_length = strategy_used if strategy_used else 2
                    logger.info(f"BALANCED SEARCH: Using {phrase_length}-word phrases for {period_desc}...")
                    period_results = self._search_time_period_keywords(project, work_item, teams_to_search, period_name, work_item_types, print_query=False, phrase_length=phrase_length)
                
                if period_results:
                    new_items = []
                    for item in period_results:
                        if item.id not in seen_ids:
                            all_results.append(item)
                            seen_ids.add(item.id)
                            new_items.append(item)
                    
                    logger.info(f"{period_desc}: Found {len(new_items)} new items")
                    
                    # Check if total results are greater than 350 (Balanced Search optimization)
                    total_count = len(all_results)
                    if total_count > 350:
                        logger.info(f"BALANCED SEARCH OPTIMIZATION: Stopping at {total_count} items (exceeds threshold of 350)")
                        break
                else:
                    logger.info(f"{period_desc}: No items found")
            
            logger.info(f"Comprehensive keyword search completed. Total items found: {len(all_results)}")
            return all_results
            
        except Exception as e:
            logger.error(f"Error in balanced keyword search with batching: {e}")
            return []
    
    def _search_time_period_keywords(self, project, work_item, teams_to_search, period_name, work_item_types, print_query=False, phrase_length=2):
        """Search a specific time period using keyword matching with configurable phrase length"""
        try:
            # Generate WIQL query for this time period using keyword matching
            wiql_query = self._generate_keyword_wiql_query(project, work_item, teams_to_search, period_name, work_item_types, phrase_length)
            
            if wiql_query:
                # Print the WIQL query for debugging (only for first period)
                if print_query:
                    logger.info("BALANCED SEARCH WIQL QUERY:")
                    logger.info("=" * 80)
                    logger.info(wiql_query)
                    logger.info("=" * 80)
                
                # Execute the query for this time period
                wiql = {"query": wiql_query}
                query_result = self.work_item_client.query_by_wiql(wiql)
                
                if query_result and hasattr(query_result, 'work_items') and query_result.work_items:
                    logger.info(f"{period_name}: Found {len(query_result.work_items)} items using keyword search")
                    return query_result.work_items
                else:
                    logger.info(f"{period_name}: No items found using keyword search")
                    return []
            else:
                logger.warning(f"{period_name}: No valid query generated")
                return []
                
        except Exception as e:
            logger.error(f"Error searching time period {period_name}: {e}")
            return []
    
    def _generate_keyword_wiql_query(self, project, work_item, teams_to_search, date_filter, work_item_types, phrase_length=2):
        """Generate WIQL query using meaningful phrase matching for balanced search with configurable phrase length"""
        try:
            # Extract meaningful phrases from title for better semantic matching
            phrases = self._extract_meaningful_phrases(work_item, phrase_length)
            
            if not phrases:
                logger.info("No meaningful phrases found for balanced search")
                return None
            
            logger.info(f"BALANCED SEARCH - Using phrases: {phrases}")
            
            # Build phrase conditions for both Title and Description fields
            phrase_conditions = []
            for phrase in phrases:
                escaped_phrase = phrase.replace("'", "''")
                # Search in both Title and Description for broader matching
                phrase_conditions.append(f"([System.Title] CONTAINS '{escaped_phrase}' OR [System.Description] CONTAINS '{escaped_phrase}')")
            
            # All conditions use CONTAINS (Azure DevOps doesn't support LIKE with wildcards)
            all_conditions = phrase_conditions
            if not all_conditions:
                return None
            
            phrase_where_clause = " OR ".join(all_conditions)
            
            # Build area path conditions for selected teams
            area_conditions = []
            try:
                import json
                import os
                mapping_file = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'team_area_paths.json')
                if os.path.exists(mapping_file):
                    with open(mapping_file, 'r', encoding='utf-8') as f:
                        mapping_data = json.load(f)
                        mappings = mapping_data.get('mappings', {})
                        
                        for team_name in teams_to_search:
                            if team_name in mappings:
                                team_data = mappings[team_name]
                                if team_data.get('verified', False):
                                    area_path = team_data.get('area_path', '')
                                    if area_path:
                                        escaped_area_path = area_path.replace("'", "''")
                                        area_conditions.append(f"[System.AreaPath] UNDER '{escaped_area_path}'")
            except Exception as e:
                logger.error(f"Error loading team area path mappings: {e}")
                return None
            
            if not area_conditions:
                logger.warning("No valid area paths found for balanced search teams")
                return None
            
            # Build the complete WIQL query
            wiql_query = f"""
            SELECT [System.Id], [System.Title], [System.WorkItemType], [System.State],
                   [System.AssignedTo], [System.CreatedBy], [System.CreatedDate], [System.Description],
                   [System.AreaPath], [System.TeamProject]
            FROM WorkItems
            WHERE [System.TeamProject] = '{project}'
            AND [System.Id] != {work_item.id}
            AND [System.State] <> 'Removed'
            AND ({phrase_where_clause})"""
            
            # Add work item type filter
            if work_item_types and len(work_item_types) > 0:
                escaped_types = [t.replace("'", "''") for t in work_item_types]
                type_conditions = " OR ".join([f"[System.WorkItemType] = '{t}'" for t in escaped_types])
                wiql_query += f"\n            AND ({type_conditions})"
            
            # Add date filter
            date_condition = self._get_date_filter_condition(date_filter)
            if date_condition:
                wiql_query += f"\n            AND {date_condition}"
            else:
                # Fallback to 180 days if no valid date filter
                wiql_query += f"\n            AND [System.CreatedDate] >= @Today - 180"
            
            # Add area path filter for selected teams
            wiql_query += f"\n            AND ({' OR '.join(area_conditions)})"
            
            # Order by creation date descending
            wiql_query += "\n            ORDER BY [System.CreatedDate] DESC"
            
            return wiql_query
            
        except Exception as e:
            logger.error(f"Error generating keyword WIQL query: {e}")
            return None
    
    def _search_time_period(self, project, work_item, teams_to_search, period_name, work_item_types, print_query=False):
        """Search a specific time period across all teams"""
        try:
            # Generate WIQL query for this time period
            wiql_query = self._generate_all_teams_wiql_query(project, work_item, teams_to_search, period_name, work_item_types)
            
            if wiql_query:
                # Print the WIQL query for debugging only if requested
                if print_query:
                    logger.info(f"LASER FOCUS WIQL QUERY ({period_name}):")
                    logger.info("=" * 80)
                    logger.info(wiql_query)
                    logger.info("=" * 80)
                
                # Execute the query for this time period
                wiql = {"query": wiql_query}
                query_result = self.work_item_client.query_by_wiql(wiql)
                
                if query_result and hasattr(query_result, 'work_items') and query_result.work_items:
                    return query_result.work_items
                else:
                    return []
            else:
                return []
                
        except Exception as e:
            logger.error(f"Error searching time period {period_name}: {e}")
            return []
    
    
    def get_work_item(self, work_item_id):
        """
        Get a specific work item by ID.
        
        Args:
            work_item_id (int): The ID of the work item to retrieve.
            
        Returns:
            WorkItem: The requested work item.
        """
        try:
            # Explicitly request the description field and other important fields
            fields = [
                'System.Id',
                'System.Title', 
                'System.Description',
                'System.WorkItemType',
                'System.State',
                'System.AssignedTo',
                'System.CreatedBy',
                'System.CreatedDate',
                'System.ChangedDate',
                'System.AreaPath',
                'System.IterationPath',
                'System.Tags',
                'System.Parent',
                'Microsoft.VSTS.Common.Priority',
                'Microsoft.VSTS.Common.Severity',
                'Microsoft.VSTS.Scheduling.Effort',
                'Microsoft.VSTS.Scheduling.StoryPoints'
            ]
            work_item = self.work_item_client.get_work_item(work_item_id, fields=fields)
            logger.info(f"Retrieved work item {work_item_id}: {work_item.fields['System.Title']}")
            return work_item
        except Exception as e:
            logger.error(f"Error retrieving work item {work_item_id}: {str(e)}")
            raise
    
    def print_work_item_details(self, work_item):
        """
        Print details of a work item.
        
        Args:
            work_item: The work item to print details for.
        """
        print("\n=== Work Item Details ===")
        print(f"ID: {work_item.id}")
        print(f"Title: {work_item.fields['System.Title']}")
        print(f"State: {work_item.fields['System.State']}")
        print(f"Type: {work_item.fields['System.WorkItemType']}")
        print(f"Created By: {work_item.fields.get('System.CreatedBy', 'Unknown')}")
        print(f"Assigned To: {work_item.fields.get('System.AssignedTo', 'Unassigned')}")
        
        if 'System.Description' in work_item.fields:
            print("\nDescription:")
            print(work_item.fields['System.Description'])
        
        if 'System.Tags' in work_item.fields:
            print(f"\nTags: {work_item.fields['System.Tags']}")
    
    def query_work_items(self, project, team=None, work_item_type=None, state=None, limit=None, enhanced_filters=None):
        """
        Query work items based on specified criteria with enhanced filtering support.
        
        Args:
            project (str): The name of the project.
            team (str, optional): The name of the team to filter by.
            work_item_type (str, optional): The type of work items to query (e.g., 'User Story', 'Bug').
            state (str, optional): The state of work items to query (e.g., 'Active', 'Closed').
            limit (int, optional): Maximum number of work items to return. If None, uses intelligent limits.
            enhanced_filters (dict, optional): Additional filters for enhanced filtering.
            
        Returns:
            list: A list of work items matching the criteria.
        """
        try:
            # Validate inputs
            if not project or not project.strip():
                logger.error("Project name is required")
                return []
            
            project = project.strip()
            
            # Clean and validate optional parameters
            if team:
                team = team.strip() if isinstance(team, str) else str(team).strip()
                if not team:
                    team = None
            
            if work_item_type:
                work_item_type = work_item_type.strip() if isinstance(work_item_type, str) else str(work_item_type).strip()
                if not work_item_type:
                    work_item_type = None
            
            if state:
                state = state.strip() if isinstance(state, str) else str(state).strip()
                if not state:
                    state = None
            
            # Validate and set intelligent limit
            if limit is None:
                # Use intelligent limits based on filters
                if enhanced_filters and any(enhanced_filters.values()):
                    limit = 19950  # Maximum limit when using enhanced filters
                elif state and state != "All":
                    limit = 15000  # High limit for specific states
                else:
                    limit = 10000  # Higher limit for broad queries
            else:
                try:
                    limit = int(limit)
                    if limit <= 0:
                        logger.warning(f"Invalid limit {limit}, using intelligent default")
                        limit = 10000
                except (ValueError, TypeError):
                    logger.warning(f"Invalid limit {limit}, using intelligent default")
                    limit = 10000
            
            # Apply intelligent maximum limit to prevent VS402337 error
            MAX_ADO_LIMIT = 19950  # Maximum possible limit under the 20,000 ADO limit
            if limit > MAX_ADO_LIMIT:
                logger.warning(f"Requested limit {limit} exceeds maximum ADO limit. Reducing to {MAX_ADO_LIMIT}")
                limit = MAX_ADO_LIMIT
            
            # For very large projects, use more conservative limits to avoid VS402337
            if limit > 10000 and not team and not work_item_type and not state:
                logger.warning(f"Large project detected with broad query. Reducing limit from {limit} to 5000 to avoid VS402337")
                limit = 5000
            
            logger.info(f"Querying work items with validated parameters:")
            logger.info(f"  Project: '{project}'")
            logger.info(f"  Team: '{team}'")
            logger.info(f"  Work Item Type: '{work_item_type}'")
            logger.info(f"  State: '{state}'")
            logger.info(f"  Limit: {limit}")
            
            if team:
                # Use enhanced team query strategy
                logger.info(f"Querying work items for team '{team}' in project '{project}' using enhanced strategy")
                work_items = self.get_team_work_items_enhanced(project, team, work_item_type, state, limit)
                
                # Apply enhanced filters if provided
                if enhanced_filters and work_items:
                    logger.info(f"Applying enhanced filters: {enhanced_filters}")
                    from .enhanced_filters import EnhancedFilterManager
                    filter_manager = EnhancedFilterManager(self)
                    work_items = filter_manager.apply_filters_to_work_items(work_items, enhanced_filters)
                    logger.info(f"After applying enhanced filters: {len(work_items)} items remaining")
                
                return work_items
            
            # No team specified - use project-wide query
            logger.info(f"Querying work items for entire project '{project}' (no team specified)")
            
            # Build the WIQL query
            wiql_query = f"""
            SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType], [System.AssignedTo], [System.CreatedDate]
            FROM workitems
            WHERE [System.TeamProject] = '{project}'
            """
            
            if work_item_type:
                wiql_query += f" AND [System.WorkItemType] = '{work_item_type}'"
            
            if state:
                wiql_query += f" AND [System.State] = '{state}'"
                logger.info(f"Added state filter to WIQL: [System.State] = '{state}'")
            
            wiql_query += f" ORDER BY [System.CreatedDate] DESC"
            
            logger.info(f"Final WIQL query: {wiql_query}")
            
            # Execute the query
            wiql = {"query": wiql_query}
            query_result = self.work_item_client.query_by_wiql(wiql).work_items
            
            if not query_result:
                logger.info("No work items found matching the criteria.")
                return []
            
            # Limit the number of results
            query_result = query_result[:limit]
            
            # Get the full work items using batch processing for better performance
            work_items = self.get_work_items_batch([int(res.id) for res in query_result])
            
            # Apply enhanced filters if provided
            if enhanced_filters and work_items:
                logger.info(f"Applying enhanced filters: {enhanced_filters}")
                from .enhanced_filters import EnhancedFilterManager
                filter_manager = EnhancedFilterManager(self)
                work_items = filter_manager.apply_filters_to_work_items(work_items, enhanced_filters)
                logger.info(f"After applying enhanced filters: {len(work_items)} items remaining")
            
            logger.info(f"Retrieved {len(work_items)} work items from project '{project}'")
            return work_items
        
        except Exception as e:
            error_msg = str(e)
            # Check for specific ADO size limit errors
            if "VS402337" in error_msg or "size limit" in error_msg.lower():
                logger.error(f"ADO size limit exceeded. Attempting intelligent fallback strategies...")
                
                # Try with more restrictive filters
                logger.info("Attempting fallback with recent items only...")
                try:
                    # Try with just recent items (last 30 days)
                    from datetime import datetime, timedelta
                    recent_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
                    
                    # Build fallback query with date filter
                    fallback_where = f"[System.TeamProject] = '{project}'"
                    if state:
                        fallback_where += f" AND [System.State] = '{state}'"
                    if work_item_type:
                        fallback_where += f" AND [System.WorkItemType] = '{work_item_type}'"
                    if team:
                        fallback_where += f" AND [System.AreaPath] UNDER '{project}\\{team}'"
                    
                    fallback_where += f" AND [System.CreatedDate] >= '{recent_date}'"
                    
                    wiql_query = f"""
                    SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType], [System.AssignedTo], [System.CreatedDate]
                    FROM workitems
                    WHERE {fallback_where}
                    ORDER BY [System.CreatedDate] DESC
                    """
                    
                    logger.info(f"Executing recent items fallback query: {wiql_query}")
                    
                    wiql = {"query": wiql_query}
                    query_result = self.work_item_client.query_by_wiql(wiql)
                    
                    if query_result.work_items:
                        work_item_ids = [int(res.id) for res in query_result.work_items[:limit]]
                        work_items = self.get_work_items_batch(work_item_ids)
                        logger.info(f"Fallback successful: Retrieved {len(work_items)} recent work items")
                        return work_items
                    else:
                        logger.warning("No recent work items found in fallback query")
                        
                except Exception as fallback_error:
                    logger.warning(f"Recent items fallback failed: {fallback_error}")
                
                # Try even more restrictive fallback (last 7 days)
                try:
                    logger.info("Attempting ultra-restrictive fallback with last 7 days...")
                    from datetime import datetime, timedelta
                    ultra_recent_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
                    
                    ultra_fallback_where = f"[System.TeamProject] = '{project}'"
                    if state:
                        ultra_fallback_where += f" AND [System.State] = '{state}'"
                    ultra_fallback_where += f" AND [System.CreatedDate] >= '{ultra_recent_date}'"
                    
                    ultra_wiql_query = f"""
                    SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType], [System.AssignedTo], [System.CreatedDate]
                    FROM workitems
                    WHERE {ultra_fallback_where}
                    ORDER BY [System.CreatedDate] DESC
                    """
                    
                    logger.info(f"Executing ultra-restrictive fallback query: {ultra_wiql_query}")
                    
                    wiql = {"query": ultra_wiql_query}
                    query_result = self.work_item_client.query_by_wiql(wiql)
                    
                    if query_result.work_items:
                        work_item_ids = [int(res.id) for res in query_result.work_items[:min(100, limit)]]
                        work_items = self.get_work_items_batch(work_item_ids)
                        logger.info(f"Ultra-restrictive fallback successful: Retrieved {len(work_items)} recent work items")
                        return work_items
                    else:
                        logger.warning("No work items found even in ultra-restrictive fallback")
                        
                except Exception as ultra_fallback_error:
                    logger.warning(f"Ultra-restrictive fallback failed: {ultra_fallback_error}")
                
                # If all fallbacks fail, raise the original error with helpful message
                raise Exception(f"ADO size limit exceeded (VS402337): The query would return more than 20,000 items. "
                              f"Current limit: {limit}. "
                              f"Try reducing the limit or adding more specific filters (team, work item type, state).")
            else:
                logger.error(f"Error querying work items: {error_msg}")
                raise
    
    def get_work_items_batch(self, work_item_ids, batch_size=200):
        """
        Retrieve multiple work items in batches for better performance.
        
        Args:
            work_item_ids (list): List of work item IDs to retrieve
            batch_size (int): Number of work items to retrieve per batch
            
        Returns:
            list: List of work items
        """
        if not work_item_ids:
            return []
        
        work_items = []
        total_ids = len(work_item_ids)
        
        logger.info(f"Retrieving {total_ids} work items in batches of {batch_size}")
        
        # Process in batches
        for i in range(0, total_ids, batch_size):
            batch_ids = work_item_ids[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}: IDs {batch_ids[0]}-{batch_ids[-1]}")
            
            try:
                # Use the Azure DevOps SDK's batch retrieval with expanded fields
                # Explicitly request the description field and other important fields
                fields = [
                    'System.Id',
                    'System.Title', 
                    'System.Description',
                    'System.WorkItemType',
                    'System.State',
                    'System.AssignedTo',
                    'System.CreatedBy',
                    'System.CreatedDate',
                    'System.ChangedDate',
                    'System.AreaPath',
                    'System.IterationPath',
                    'System.Tags',
                    'System.Parent',
                    'Microsoft.VSTS.Common.Priority',
                    'Microsoft.VSTS.Common.Severity',
                    'Microsoft.VSTS.Scheduling.Effort',
                    'Microsoft.VSTS.Scheduling.StoryPoints'
                ]
                batch_result = self.work_item_client.get_work_items(batch_ids, fields=fields)
                work_items.extend(batch_result)
                logger.info(f"Successfully retrieved batch of {len(batch_result)} work items with expanded fields")
                
            except Exception as e:
                logger.warning(f"Batch retrieval failed for IDs {batch_ids}: {e}")
                # Fallback to individual retrieval for this batch
                logger.info("Falling back to individual work item retrieval for failed batch")
                for work_item_id in batch_ids:
                    try:
                        work_item = self.work_item_client.get_work_item(work_item_id)
                        work_items.append(work_item)
                    except Exception as individual_error:
                        logger.warning(f"Could not retrieve work item {work_item_id}: {individual_error}")
                        continue
        
        logger.info(f"Batch retrieval completed: {len(work_items)}/{total_ids} work items retrieved")
        return work_items
    
    def print_work_items_summary(self, work_items):
        """
        Print a summary of work items.
        
        Args:
            work_items (list): The list of work items to summarize.
        """
        if not work_items:
            print("No work items to display.")
            return
        
        print("\n=== Work Items Summary ===")
        print(f"{'ID':<8} {'Type':<12} {'State':<10} {'Title'}")
        print("-" * 80)
        
        for item in work_items:
            item_id = item.id
            item_type = item.fields.get('System.WorkItemType', 'Unknown')
            item_state = item.fields.get('System.State', 'Unknown')
            item_title = item.fields.get('System.Title', 'No Title')
            
            # Truncate title if too long
            if len(item_title) > 50:
                item_title = item_title[:47] + "..."
            
            print(f"{item_id:<8} {item_type:<12} {item_state:<10} {item_title}")
    
    def get_team_info(self, project, team):
        """Get detailed information about a specific team."""
        try:
            logger.info(f"Getting team info for team '{team}' in project '{project}'")
            core_client = self.connection.clients.get_core_client()
            team_info = core_client.get_team(project, team)
            
            logger.info(f"Team info retrieved successfully")
            logger.info(f"Team object: {team_info}")
            logger.info(f"Team attributes: {[attr for attr in dir(team_info) if not attr.startswith('_')]}")
            
            # Extract key information
            team_data = {}
            for attr in ['id', 'name', 'description', 'url', 'identity_url', 'project_name', 'project_id']:
                if hasattr(team_info, attr):
                    team_data[attr] = getattr(team_info, attr)
            
            # Try to get area path information
            try:
                if hasattr(team_info, 'default_area_path'):
                    team_data['default_area_path'] = team_info.default_area_path
                    logger.info(f"Team default area path: {team_info.default_area_path}")
                else:
                    logger.warning(f"Team does not have default_area_path attribute")
                    team_data['default_area_path'] = None
            except Exception as e:
                logger.warning(f"Could not get team area path: {e}")
                team_data['default_area_path'] = None
            
            return team_data
            
        except Exception as e:
            logger.error(f"Error getting team info for team '{team}' in project '{project}': {e}")
            return None
    
    def test_team_context(self, project, team):
        """Test team context and area path configuration."""
        try:
            logger.info(f"Testing team context for team '{team}' in project '{project}'")
            
            # Test 1: Get team info
            logger.info("Test 1: Getting team information...")
            team_info = self.get_team_info(project, team)
            if not team_info:
                logger.error("[ERROR] Failed to get team information")
                return False
            
            logger.info("[SUCCESS] Team information retrieved successfully")
            
            # Test 2: Check area path
            logger.info("Test 2: Checking team area path...")
            if team_info.get('default_area_path'):
                logger.info(f"[SUCCESS] Team has area path: {team_info['default_area_path']}")
            else:
                logger.warning("[WARNING] Team does not have a default area path configured")
                logger.warning("This will cause team-specific queries to fail")
            
            # Test 3: Try team backlog access
            logger.info("Test 3: Testing team backlog access...")
            try:
                work_client = self.connection.clients.get_work_client()
                team_context = {"project": project, "team": team}
                
                # Try to get backlog levels
                backlog_levels = work_client.get_backlog_levels(team_context)
                logger.info(f"[SUCCESS] Team backlog levels accessible: {len(backlog_levels) if backlog_levels else 0} levels found")
                
                # Try to get backlog work items
                if backlog_levels:
                    try:
                        backlog_items = work_client.get_backlog_level_work_items(
                            team_context=team_context,
                            backlog_id="Microsoft.RequirementCategory"
                        )
                        if backlog_items and hasattr(backlog_items, 'work_items'):
                            logger.info(f"[SUCCESS] Team backlog work items accessible: {len(backlog_items.work_items)} items found")
                        else:
                            logger.warning("[WARNING] Team backlog work items not accessible or empty")
                    except Exception as e:
                        logger.warning(f"[WARNING] Could not access team backlog work items: {e}")
                else:
                    logger.warning("[WARNING] No backlog levels found for team")
                    
            except Exception as e:
                logger.warning(f"[WARNING] Team backlog access failed: {e}")
            
            # Test 4: Test area path query
            logger.info("Test 4: Testing area path query...")
            if team_info.get('default_area_path'):
                try:
                    area_path = team_info['default_area_path']
                    wiql_query = f"""
                    SELECT [System.Id]
                    FROM workitems
                    WHERE [System.TeamProject] = '{project}'
                    AND [System.AreaPath] UNDER '{area_path}'
                    ORDER BY [System.CreatedDate] DESC
                    """
                    
                    wiql = {"query": wiql_query}
                    query_result = self.work_item_client.query_by_wiql(wiql).work_items
                    
                    if query_result:
                        logger.info(f"[SUCCESS] Area path query successful: {len(query_result)} work items found")
                    else:
                        logger.warning("[WARNING] Area path query returned no results")
                        
                except Exception as e:
                    logger.warning(f"[WARNING] Area path query failed: {e}")
            else:
                logger.warning("[WARNING] Cannot test area path query - no area path configured")
            
            logger.info("Team context testing completed")
            return True
            
        except Exception as e:
            logger.error(f"Error testing team context: {e}")
            return False
    
    def query_work_items_paginated(self, project, team=None, work_item_type=None, state=None, page_size=500, max_pages=40):
        """
        Query work items with pagination to handle large result sets without hitting ADO limits.
        
        Args:
            project (str): The name of the project.
            team (str, optional): The name of the team to filter by.
            work_item_type (str, optional): The type of work items to query.
            state (str, optional): The state of work items to query.
            page_size (int, optional): Number of items per page (max 20000 for ADO).
            max_pages (int, optional): Maximum number of pages to retrieve.
            
        Returns:
            list: A list of work items matching the criteria.
        """
        try:
            # Ensure page size doesn't exceed ADO limits
            if page_size > 20000:
                logger.warning(f"Page size {page_size} exceeds ADO limit. Reducing to 20000")
                page_size = 20000
            
            all_work_items = []
            page_count = 0
            
            # Build base WIQL query with proper escaping
            escaped_project = project.replace("'", "''")
            base_where = f"[System.TeamProject] = '{escaped_project}'"
            
            if team:
                try:
                    core_client = self.connection.clients.get_core_client()
                    team_info = core_client.get_team(project, team)
                    
                    if hasattr(team_info, 'default_area_path'):
                        area_path = team_info.default_area_path
                        escaped_area_path = area_path.replace("'", "''")
                        base_where += f" AND [System.AreaPath] UNDER '{escaped_area_path}'"
                        logger.info(f"Using team area path: {area_path}")
                except Exception as e:
                    logger.warning(f"Could not get team area path: {e}")
            
            if work_item_type:
                escaped_work_item_type = work_item_type.replace("'", "''")
                base_where += f" AND [System.WorkItemType] = '{escaped_work_item_type}'"
            
            if state:
                escaped_state = state.replace("'", "''")
                base_where += f" AND [System.State] = '{escaped_state}'"
            
            # Use continuation token for pagination
            continuation_token = None
            
            while page_count < max_pages:
                # Build WIQL query for this page with proper formatting
                wiql_query = f"""SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType], [System.AssignedTo], [System.CreatedDate]
FROM workitems
WHERE {base_where}
ORDER BY [System.Id]"""
                
                logger.info(f"Executing paginated WIQL query (page {page_count + 1}): {wiql_query}")
                
                # Execute query with continuation token if available
                wiql = {"query": wiql_query}
                if continuation_token:
                    wiql["continuationToken"] = continuation_token
                
                query_result = self.work_item_client.query_by_wiql(wiql)
                
                if not query_result.work_items:
                    logger.info(f"No more work items found after page {page_count}")
                    break
                
                # Get full work items for this page using batch processing
                # Limit the number of work items to avoid hitting ADO limits
                work_item_ids = [int(res.id) for res in query_result.work_items[:page_size]]
                page_work_items = self.get_work_items_batch(work_item_ids)
                
                all_work_items.extend(page_work_items)
                page_count += 1
                
                logger.info(f"Retrieved page {page_count}: {len(page_work_items)} work items (total: {len(all_work_items)})")
                
                # Stop if we've reached a reasonable total limit
                if len(all_work_items) >= 19950:  # Stay under the 20k limit
                    logger.info(f"Reached maximum safe limit of {len(all_work_items)} work items")
                    break
                
                # Check if there are more results
                if hasattr(query_result, 'continuation_token') and query_result.continuation_token:
                    continuation_token = query_result.continuation_token
                else:
                    logger.info("No continuation token - reached end of results")
                    break
            
            logger.info(f"Pagination complete: Retrieved {len(all_work_items)} work items across {page_count} pages")
            return all_work_items
            
        except Exception as e:
            error_msg = str(e)
            if "VS402337" in error_msg or "size limit" in error_msg.lower():
                logger.error(f"ADO size limit exceeded even with pagination. Attempting recent items fallback...")
                
                # Try with recent items only (last 30 days) as final fallback
                try:
                    from datetime import datetime, timedelta
                    recent_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
                    
                    logger.info(f"Attempting fallback with recent items (last 30 days from {recent_date})...")
                    
                    # Build fallback query with date filter
                    fallback_where = f"[System.TeamProject] = '{escaped_project}'"
                    if state:
                        fallback_where += f" AND [System.State] = '{escaped_state}'"
                    fallback_where += f" AND [System.CreatedDate] >= '{recent_date}'"
                    
                    fallback_query = f"""SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType], [System.AssignedTo], [System.CreatedDate]
FROM workitems
WHERE {fallback_where}
ORDER BY [System.CreatedDate] DESC"""
                    
                    logger.info(f"Executing fallback WIQL query: {fallback_query}")
                    
                    wiql = {"query": fallback_query}
                    query_result = self.work_item_client.query_by_wiql(wiql)
                    
                    if query_result.work_items:
                        # Limit to reasonable number for fallback
                        work_item_ids = [int(res.id) for res in query_result.work_items[:min(10000, len(query_result.work_items))]]
                        fallback_work_items = self.get_work_items_batch(work_item_ids)
                        logger.info(f"Fallback successful: Retrieved {len(fallback_work_items)} recent work items")
                        return fallback_work_items
                    else:
                        logger.warning("No recent work items found in fallback query")
                        
                except Exception as fallback_error:
                    logger.warning(f"Recent items fallback failed: {fallback_error}")
                
                # If all fallbacks fail, raise the original error with helpful message
                raise Exception(f"ADO size limit exceeded (VS402337): Even with pagination and recent items fallback, the query would return too many items. "
                              f"Try adding more specific filters (team, work item type, state) or reducing page size.")
            else:
                logger.error(f"Error in paginated work item query: {error_msg}")
                raise
    
    def get_board_columns(self, project, team, board_name):
        """
        Get the columns of a specific board.
        
        Args:
            project (str): The name of the project.
            team (str): The name of the team.
            board_name (str): The name of the board.
            
        Returns:
            list: The columns of the board.
        """
        try:
            # Create team context
            team_context = {
                "project": project,
                "team": team
            }
            
            # Get board
            board = self.work_client.get_board(team_context, board_name)
            columns = board.columns
            
            logger.info(f"Retrieved {len(columns)} columns from board '{board_name}'")
            return columns
        
        except Exception as e:
            logger.error(f"Error retrieving board columns: {str(e)}")
            raise
    
    def print_board_columns(self, columns):
        """
        Print the columns of a board.
        
        Args:
            columns (list): The columns to print.
        """
        if not columns:
            print("No columns to display.")
            return
        
        print("\n=== Board Columns ===")
        print(f"{'Name':<20} {'WIP Limit':<10} {'Item Limit':<10} {'Is Split'}")
        print("-" * 60)
        
        for column in columns:
            name = column.name
            wip_limit = column.max_limit if column.max_limit is not None else "None"
            item_limit = column.item_limit if column.item_limit is not None else "None"
            is_split = "Yes" if column.is_split else "No"
            
            print(f"{name:<20} {wip_limit:<10} {item_limit:<10} {is_split}")
    
    def create_work_item(self, project, work_item_type, title, description=None, assigned_to=None, tags=None):
        """
        Create a new work item.
        
        Args:
            project (str): The name of the project.
            work_item_type (str): The type of work item to create (e.g., 'User Story', 'Bug').
            title (str): The title of the work item.
            description (str, optional): The description of the work item.
            assigned_to (str, optional): The person to assign the work item to.
            tags (str, optional): Tags for the work item, semicolon-separated.
            
        Returns:
            WorkItem: The created work item.
        """
        # Create a patch document for the new work item
        document = [
            {
                "op": "add",
                "path": "/fields/System.Title",
                "value": title
            }
        ]
        
        if description:
            document.append({
                "op": "add",
                "path": "/fields/System.Description",
                "value": f"<div>{description}</div>"
            })
        
        if assigned_to:
            document.append({
                "op": "add",
                "path": "/fields/System.AssignedTo",
                "value": assigned_to
            })
        
        if tags:
            document.append({
                "op": "add",
                "path": "/fields/System.Tags",
                "value": tags
            })
        
        try:
            # Create the work item
            new_work_item = self.work_item_client.create_work_item(
                document=document,
                project=project,
                type=work_item_type
            )
            
            logger.info(f"Created work item {new_work_item.id}: {title}")
            return new_work_item
        
        except Exception as e:
            logger.error(f"Error creating work item: {str(e)}")
            raise
    
    def update_work_item(self, work_item_id, title=None, description=None, state=None, assigned_to=None, tags=None):
        """
        Update an existing work item.
        
        Args:
            work_item_id (int): The ID of the work item to update.
            title (str, optional): The new title of the work item.
            description (str, optional): The new description of the work item.
            state (str, optional): The new state of the work item.
            assigned_to (str, optional): The person to assign the work item to.
            tags (str, optional): Tags for the work item, semicolon-separated.
            
        Returns:
            WorkItem: The updated work item.
        """
        # Create a patch document for the work item update
        document = []
        
        if title:
            document.append({
                "op": "add",
                "path": "/fields/System.Title",
                "value": title
            })
        
        if description:
            document.append({
                "op": "add",
                "path": "/fields/System.Description",
                "value": f"<div>{description}</div>"
            })
        
        if state:
            document.append({
                "op": "add",
                "path": "/fields/System.State",
                "value": state
            })
        
        if assigned_to:
            document.append({
                "op": "add",
                "path": "/fields/System.AssignedTo",
                "value": assigned_to
            })
        
        if tags:
            document.append({
                "op": "add",
                "path": "/fields/System.Tags",
                "value": tags
            })
        
        # Add a history entry
        document.append({
            "op": "add",
            "path": "/fields/System.History",
            "value": f"<div>Updated via Python SDK on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>"
        })
        
        try:
            # Update the work item
            updated_work_item = self.work_item_client.update_work_item(
                document=document,
                id=work_item_id
            )
            
            logger.info(f"Updated work item {work_item_id}")
            return updated_work_item
        
        except Exception as e:
            logger.error(f"Error updating work item {work_item_id}: {str(e)}")
            raise
    
    def get_work_items(self, project=None, max_items=None):
        """
        Get work items with optional project and limit parameters.
        
        Args:
            project (str): The project name (optional)
            max_items (int): Maximum number of items to return (optional)
            
        Returns:
            list: A list of work items.
        """
        try:
            # Use the current project from session if not provided
            if not project:
                # Try to get default project from configuration
                config_file = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'ado_settings.txt')
                if os.path.exists(config_file):
                    with open(config_file, 'r') as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith('project=') and '=' in line:
                                project = line.split('=', 1)[1]
                                break
            
            if not project:
                logger.error("No project specified for get_work_items")
                return []
            
            # Use the existing query_work_items method
            work_items = self.query_work_items(project, limit=max_items)
            return work_items
            
        except Exception as e:
            logger.error(f"Error in get_work_items: {e}")
            return []

    def get_work_items_by_area_path(self, area_path, limit=100):
        """
        Get work items filtered by area path.
        
        Args:
            area_path (str): The area path to filter by
            limit (int): Maximum number of items to return
            
        Returns:
            list: A list of work items from the specified area path.
        """
        try:
            # Get the current project
            project = None
            config_file = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'ado_settings.txt')
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith('project=') and '=' in line:
                            project = line.split('=', 1)[1]
                            break
            
            if not project:
                logger.error("No project specified for get_work_items_by_area_path")
                return []
            
            # Create WIQL query to filter by area path
            wiql_query = f"""
            SELECT [System.Id], [System.Title], [System.Description], [System.Tags], 
                   [System.WorkItemType], [System.State], [System.AssignedTo], 
                   [System.AreaPath], [System.TeamProject]
            FROM WorkItems 
            WHERE [System.AreaPath] UNDER '{area_path}' 
            ORDER BY [System.ChangedDate] DESC
            """
            
            # Execute the WIQL query directly
            wiql = {"query": wiql_query}
            query_result = self.work_item_client.query_by_wiql(wiql)
            
            if not query_result or not query_result.work_items:
                logger.info(f"No work items found in area path: {area_path}")
                return []
            
            # Get work item details
            work_item_ids = [item.id for item in query_result.work_items[:limit]]
            work_items = self.get_work_items_batch(work_item_ids)
            
            logger.info(f"Found {len(work_items)} work items in area path: {area_path}")
            return work_items
            
        except Exception as e:
            logger.error(f"Error in get_work_items_by_area_path: {e}")
            return []

    def get_projects(self):
        """
        Get all projects from the Azure DevOps organization.
        
        Returns:
            list: A list of project objects with name, id, and description attributes.
        """
        try:
            core_client = self.connection.clients.get_core_client()
            projects = core_client.get_projects()
            
            project_list = []
            for project in projects:
                project_data = {
                    'name': project.name if hasattr(project, 'name') else str(project),
                    'id': project.id if hasattr(project, 'id') else '',
                    'description': project.description if hasattr(project, 'description') else '',
                    'url': project.url if hasattr(project, 'url') else '',
                    'state': project.state if hasattr(project, 'state') else ''
                }
                project_list.append(project_data)
            
            # Sort projects alphabetically by name
            project_list.sort(key=lambda x: x['name'].lower())
            
            logger.info(f"Retrieved {len(project_list)} projects")
            return project_list
            
        except Exception as e:
            logger.error(f"Error getting projects: {e}")
            return []

    def get_teams(self, project):
        """
        Get all teams for a specific project.
        
        Args:
            project (str): The name of the project.
            
        Returns:
            list: A list of team objects with name, id, and description attributes.
        """
        try:
            # Try using the Azure DevOps SDK's core client first
            try:
                from azure.devops.connection import Connection
                core_client = self.connection.clients.get_core_client()
                
                # Get project first to ensure it exists
                project_info = core_client.get_project(project)
                logger.info(f"Found project: {project_info.name}")
                
                # Try to get teams using the core client with pagination
                all_teams = []
                skip = 0
                top = 1000  # Maximum allowed by Azure DevOps API
                
                logger.info(f"Starting SDK teams retrieval with top={top}, skip={skip}")
                
                while True:
                    teams = core_client.get_teams(project, top=top, skip=skip)
                    if not teams:
                        logger.info("No teams returned from SDK, breaking loop")
                        break  # No more teams to fetch
                    
                    logger.info(f"SDK returned {len(teams)} teams in this batch")
                    
                    # Convert to a list of objects with consistent interface
                    for team in teams:
                        team_obj = type('Team', (), {
                            'name': team.name if hasattr(team, 'name') else str(team),
                            'id': team.id if hasattr(team, 'id') else '',
                            'description': team.description if hasattr(team, 'description') else '',
                            'url': team.url if hasattr(team, 'url') else '',
                            'identity_url': team.identity_url if hasattr(team, 'identity_url') else ''
                        })()
                        all_teams.append(team_obj)
                    
                    logger.info(f"Retrieved batch of {len(teams)} teams using core client (total so far: {len(all_teams)})")
                    
                    # Check if we got fewer teams than requested (means we've reached the end)
                    if len(teams) < top:
                        logger.info(f"Got fewer teams than requested ({len(teams)} < {top}), reached end")
                        break
                    
                    skip += top
                    logger.info(f"Incrementing skip to {skip}")
                
                if all_teams:
                    logger.info(f"Retrieved total of {len(all_teams)} teams using core client")
                    return all_teams
                    
            except Exception as sdk_error:
                logger.warning(f"SDK method failed: {sdk_error}, trying REST API...")
            
            # Fallback to REST API with proper Basic Auth and pagination
            all_teams = []
            skip = 0
            top = 1000  # Maximum allowed by Azure DevOps API
            
            logger.info(f"Starting REST API teams retrieval with top={top}, skip={skip}")
            
            while True:
                teams_url = f"{self.organization_url}/{project}/_apis/teams?api-version=6.0&$top={top}&$skip={skip}"
                
                # Create a new session with proper Basic Auth
                import requests
                import base64
                
                # Encode the PAT properly for Basic Auth
                credentials = base64.b64encode(f":{self.personal_access_token}".encode()).decode()
                
                headers = {
                    'Authorization': f'Basic {credentials}',
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                }
                
                logger.info(f"Making teams API request to: {teams_url}")
                logger.info(f"Using Basic Auth with PAT length: {len(self.personal_access_token)}")
                
                response = requests.get(teams_url, headers=headers)
                
                # Log response details for debugging
                logger.info(f"Response status: {response.status_code}")
                
                if response.status_code == 200:
                    teams_data = response.json()
                    teams = teams_data.get('value', [])
                    
                    logger.info(f"REST API returned {len(teams)} teams in this batch")
                    
                    if not teams:
                        logger.info("No teams returned from REST API, breaking loop")
                        break  # No more teams to fetch
                    
                    # Convert to a list of objects with consistent interface
                    for team in teams:
                        team_obj = type('Team', (), {
                            'name': team.get('name', ''),
                            'id': team.get('id', ''),
                            'description': team.get('description', ''),
                            'url': team.get('url', ''),
                            'identity_url': team.get('identityUrl', '')
                        })()
                        all_teams.append(team_obj)
                    
                    logger.info(f"Retrieved batch of {len(teams)} teams (total so far: {len(all_teams)})")
                    
                    # Check if we got fewer teams than requested (means we've reached the end)
                    if len(teams) < top:
                        logger.info(f"Got fewer teams than requested ({len(teams)} < {top}), reached end")
                        break
                    
                    skip += top
                    logger.info(f"Incrementing skip to {skip}")
                else:
                    logger.error(f"Teams API failed with status {response.status_code}")
                    logger.error(f"Response text: {response.text}")
                    raise Exception(f"HTTP {response.status_code}: {response.text}")
            
            logger.info(f"Retrieved total of {len(all_teams)} teams from project '{project}' using REST API")
            return all_teams
                
        except Exception as e:
            logger.error(f"Error retrieving teams for project '{project}': {str(e)}")
            raise
    
    def query_related_work_items(self, project, work_item_id):
        """
        Query for work items related to a specific work item using intelligent title-based AI search.
        
        Args:
            project (str): The name of the project.
            work_item_id (int): The ID of the work item to find related items for.
            
        Returns:
            list: A list of related work item objects.
        """
        try:
            # First get the work item to access its fields
            work_item_client = self.connection.clients.get_work_item_tracking_client()
            work_item = work_item_client.get_work_item(work_item_id)
            
            # Use intelligent title-based search instead of basic relationship matching
            
            # Generate intelligent WIQL query based on work item title
            wiql_query = self._generate_intelligent_wiql_query(project, work_item)
            
            if not wiql_query:
                logger.info(f"Could not generate intelligent query for work item {work_item_id}, falling back to basic search")
                return self._fallback_basic_search(project, work_item)

            # Print WIQL query to terminal for debugging
            print("\n" + "="*80)
            print(f"[QUERY] INTELLIGENT WIQL QUERY")
            print("="*80)
            print(wiql_query)
            print("="*80 + "\n")
            
            # Execute the query
            wiql = {"query": wiql_query}
            query_result = work_item_client.query_by_wiql(wiql)
            
            if query_result and hasattr(query_result, 'work_items'):
                related_items = []
                for item in query_result.work_items:
                    # Get the full work item details
                    full_item = work_item_client.get_work_item(item.id)
                    related_items.append(full_item)
                
                logger.info(f"Found {len(related_items)} related work items using AI title search for work item {work_item_id}")
                return related_items
            else:
                logger.info(f"No related work items found using AI search for work item {work_item_id}")
                return []
                
        except Exception as e:
            logger.error(f"Error in AI-powered related work items search for work item {work_item_id}: {str(e)}")
            # Fallback to basic search if AI search fails
            try:
                work_item_client = self.connection.clients.get_work_item_tracking_client()
                work_item = work_item_client.get_work_item(work_item_id)
                return self._fallback_basic_search(project, work_item)
            except:
                return []
    
    def _generate_intelligent_wiql_query_for_team(self, project, work_item, team_area_path=None):
        """
        Generate intelligent WIQL query with title-based CONTAINS clauses for a specific team.
        This reduces query complexity by targeting one team at a time.
        
        Args:
            project (str): The project name
            work_item: The work item object to analyze
            team_area_path (str): Optional area path for the specific team
            
        Returns:
            str: WIQL query string with intelligent title-based matching for the team
        """
        try:
            # Get work item details - handle different object structures
            if hasattr(work_item, 'fields'):
                # Azure DevOps work item object
                work_item_title = work_item.fields.get('System.Title', '').strip()
                work_item_type = work_item.fields.get('System.WorkItemType', '')
                area_path = work_item.fields.get('System.AreaPath', '')
            elif hasattr(work_item, 'title'):
                # Dictionary-like work item object
                work_item_title = work_item.title.strip()
                work_item_type = getattr(work_item, 'workItemType', '')
                area_path = getattr(work_item, 'areaPath', '')
            elif isinstance(work_item, dict):
                # Dictionary work item object
                work_item_title = work_item.get('title', '').strip()
                work_item_type = work_item.get('workItemType', '')
                area_path = work_item.get('areaPath', '')
            else:
                                return None
            
            if not work_item_title or len(work_item_title) < 5:
                return None
            
            # Generate intelligent phrase combinations from the title
            title_phrases = self._generate_title_phrase_combinations(work_item_title)
            
            if not title_phrases:
                return None
            
            # Build CONTAINS clauses for title-based matching
            title_conditions = []
            for phrase in title_phrases:
                # Escape single quotes in the phrase
                escaped_phrase = phrase.replace("'", "''")
                title_conditions.append(f"[System.Title] CONTAINS '{escaped_phrase}'")
            
            # Combine all title conditions with OR
            title_where_clause = " OR ".join(title_conditions)
            
            # Build the complete WIQL query
            wiql_query = f"""
            SELECT [System.Id], [System.Title], [System.WorkItemType], [System.State],
                   [System.AssignedTo], [System.CreatedBy], [System.CreatedDate], [System.Description]
            FROM WorkItems
            WHERE [System.TeamProject] = '{project}'
            AND [System.Id] != {work_item.id}
            AND [System.State] <> 'Removed'
            AND ({title_where_clause})"""
            
            # Add work item type filter if available (make it optional for better results)
            if work_item_type:
                wiql_query += f"\n            AND ([System.WorkItemType] = '{work_item_type}' OR [System.WorkItemType] = 'User Story' OR [System.WorkItemType] = 'Task')"
            
            # Add date filter to get last 6 months of data (1 year causes timeout)
            wiql_query += f"\n            AND [System.CreatedDate] >= @Today - 180"
            
            # Add team-specific area path filter if provided
            if team_area_path:
                wiql_query += f"\n            AND [System.AreaPath] UNDER '{team_area_path}'"
            
            # Order by creation date descending
            wiql_query += "\n            ORDER BY [System.CreatedDate] DESC"
            
            return wiql_query
            
        except Exception as e:
            logger.error(f"Error generating intelligent WIQL query: {str(e)}")
            return None
    
    def _execute_team_based_intelligent_search(self, project, work_item, max_results_per_team=20):
        """
        Execute intelligent search across filtered teams to avoid timeout.
        Only searches specific team groups like accessibility or practical law teams.
        
        Args:
            project (str): The project name
            work_item: The work item object to analyze
            max_results_per_team (int): Maximum results per team to prevent timeout
            
        Returns:
            list: Combined list of work items from filtered teams
        """
        try:
            all_results = []
            seen_ids = set()
            
            # Get all teams for the project
            all_teams = self.get_teams(project)
            if not all_teams:
                return []
            
            # Filter teams to only include relevant groups
            # Focus on accessibility, practical law, and core teams
            team_patterns = [
                'accessibility',
                'practical law',
                'core',
                'uk',
                'connect',
                'compliance'
            ]
            
            filtered_teams = []
            for team in all_teams:
                team_name_lower = team.name.lower()
                if any(pattern in team_name_lower for pattern in team_patterns):
                    filtered_teams.append(team)
                
                # Additional check: if it's an accessibility team, include it regardless of pattern matching
                if 'accessibility' in team_name_lower and team not in filtered_teams:
                    filtered_teams.append(team)
            
            if not filtered_teams:
                return []
            
            for i, team in enumerate(filtered_teams):
                try:
                    # Get team information from Azure DevOps API
                    team_info = None
                    try:
                        team_info = self.connection.clients.get_core_client().get_team(project, team.name)
                        logger.info(f"Retrieved team info for '{team.name}': {team_info.name if team_info else 'None'}")
                    except Exception as e:
                        logger.warning(f"Could not get team info for '{team.name}': {e}")
                    
                    # Generate team-specific query using team context
                    wiql_query = self._generate_team_based_wiql_query(project, work_item, team.name, team_info)
                    
                    if wiql_query:
                        print(f"[INFO] Team {i+1}/{len(filtered_teams)}: {team.name}")
                        
                        # Print the actual WIQL query being executed
                        print(f"[QUERY] WIQL Query for {team.name}:")
                        print(f"   {wiql_query}")
                        print()
                        
                        # Execute query for this team
                        work_item_client = self.connection.clients.get_work_item_tracking_client()
                        wiql = {"query": wiql_query}
                        query_result = work_item_client.query_by_wiql(wiql)
                        
                        if query_result and hasattr(query_result, 'work_items') and query_result.work_items:
                            # Limit results to avoid API issues and improve performance
                            team_results = query_result.work_items[:max_results_per_team]
                            print(f"   Found {len(team_results)} items (limited to {max_results_per_team})")
                            
                            # Add unique items to combined results
                            for item in team_results:
                                if item.id not in seen_ids:
                                    all_results.append(item)
                                    seen_ids.add(item.id)
                        else:
                            print(f"   No items found")
                    else:
                        print(f"   Could not generate query for team {team.name}")
                        
                except Exception as team_error:
                    print(f"[ERROR] Error querying team {team.name}: {team_error}")
                    continue
            
            print(f"[SUCCESS] Team-based search completed: {len(all_results)} unique items from {len(filtered_teams)} teams")
            return all_results
            
        except Exception as e:
            logger.error(f"Error in team-based intelligent search: {str(e)}")
            return []
    
    def _execute_phased_intelligent_search(self, project, work_item, selected_team_name=None, max_results_per_team=10):
        """
        Execute intelligent search in two phases to avoid timeout:
        1. First: Search only the selected team
        2. Second: If needed, search all teams in the same group
        
        Args:
            project (str): The project name
            work_item: The work item object to analyze
            selected_team_name (str): The currently selected team name
            max_results_per_team (int): Maximum results per team to prevent timeout
            
        Returns:
            list: Combined list of work items from phased search
        """
        try:
            all_results = []
            seen_ids = set()
            
            # Get all teams for the project
            all_teams = self.get_teams(project)
            if not all_teams:
                return []
            
            # Phase 1: Search selected team first
            if selected_team_name:
                print(f"[PHASE1] Phase 1: Searching selected team '{selected_team_name}'")
                selected_team = None
                for team in all_teams:
                    if team.name == selected_team_name:
                        selected_team = team
                        break
                
                if selected_team:
                    team_results = self._search_single_team(project, work_item, selected_team, max_results_per_team)
                    if team_results:
                        for item in team_results:
                            if item.id not in seen_ids:
                                all_results.append(item)
                                seen_ids.add(item.id)
                        print(f"[SUCCESS] Phase 1: Found {len(team_results)} items from selected team")
                    else:
                        print(f"[WARNING] Phase 1: No items found in selected team")
                else:
                    print(f"[WARNING] Phase 1: Selected team '{selected_team_name}' not found")
            
            # Phase 2: If we have few results, search team group
            if len(all_results) < 5:  # If we have less than 5 results, expand to team group
                print(f"[PHASE2] Phase 2: Expanding to team group (current results: {len(all_results)})")
                
                # Determine team group based on selected team or work item area path
                team_group_patterns = self._get_team_group_patterns(selected_team_name, work_item)
                
                # Filter teams by group patterns
                group_teams = []
                for team in all_teams:
                    team_name_lower = team.name.lower()
                    if any(pattern.lower() in team_name_lower for pattern in team_group_patterns):
                        # Skip the selected team as we already searched it
                        if not selected_team_name or team.name != selected_team_name:
                            group_teams.append(team)
                
                if group_teams:
                    print(f"[INFO] Phase 2: Searching {len(group_teams)} teams in group: {team_group_patterns}")
                    
                    for i, team in enumerate(group_teams):
                        try:
                            team_results = self._search_single_team(project, work_item, team, max_results_per_team)
                            if team_results:
                                for item in team_results:
                                    if item.id not in seen_ids:
                                        all_results.append(item)
                                        seen_ids.add(item.id)
                                print(f"   Team {i+1}/{len(group_teams)}: {team.name} - Found {len(team_results)} items")
                            else:
                                print(f"   Team {i+1}/{len(group_teams)}: {team.name} - No items")
                        except Exception as team_error:
                            print(f"[ERROR] Error querying team {team.name}: {team_error}")
                            continue
                else:
                    print(f"[WARNING] Phase 2: No teams found in group patterns: {team_group_patterns}")
            else:
                print(f"[SUCCESS] Phase 2: Skipped (sufficient results from Phase 1: {len(all_results)})")
            
            print(f"[SUCCESS] Phased search completed: {len(all_results)} unique items total")
            return all_results
            
        except Exception as e:
            logger.error(f"Error in phased intelligent search: {str(e)}")
            return []
    
    def _search_single_team(self, project, work_item, team, max_results_per_team):
        """Search a single team for related work items using team-based queries."""
        try:
            # Get team information from Azure DevOps API
            team_info = None
            try:
                team_info = self.connection.clients.get_core_client().get_team(project, team.name)
                logger.info(f"Retrieved team info for '{team.name}': {team_info.name if team_info else 'None'}")
            except Exception as e:
                logger.warning(f"Could not get team info for '{team.name}': {e}")
            
            # Generate team-specific query using team context instead of area path
            wiql_query = self._generate_team_based_wiql_query(project, work_item, team.name, team_info)
            
            # Print the actual WIQL query being executed
            print(f"[QUERY] WIQL Query for {team.name}:")
            print(f"   {wiql_query}")
            print()
            
            if not wiql_query:
                return []
            
            # Execute query for this team
            work_item_client = self.connection.clients.get_work_item_tracking_client()
            wiql = {"query": wiql_query}
            query_result = work_item_client.query_by_wiql(wiql)
            
            if query_result and hasattr(query_result, 'work_items') and query_result.work_items:
                # Limit results to avoid API issues and improve performance
                limited_results = query_result.work_items[:max_results_per_team]
                print(f"   Found {len(limited_results)} items (limited to {max_results_per_team})")
                return limited_results
            else:
                return []
                
        except Exception as e:
            print(f"[ERROR] Error searching team {team.name}: {e}")
            return []
    
    def _get_team_group_patterns(self, selected_team_name, work_item):
        """Determine team group patterns based on selected team or work item."""
        patterns = []
        
        # If we have a selected team, determine group from team name
        if selected_team_name:
            team_name_lower = selected_team_name.lower()
            if 'accessibility' in team_name_lower:
                # Search all accessibility teams - be more inclusive
                patterns = ['accessibility', 'practical law - accessibility', 'practical law accessibility']
            elif 'practical law' in team_name_lower or 'practicallaw' in team_name_lower:
                # Search all practical law teams
                patterns = ['practical law', 'practicallaw']
            elif 'core' in team_name_lower:
                # Search all core teams
                patterns = ['core']
            elif 'uk' in team_name_lower:
                # Search all UK teams
                patterns = ['uk']
            elif 'connect' in team_name_lower:
                # Search all connect teams
                patterns = ['connect']
            elif 'compliance' in team_name_lower:
                # Search all compliance teams
                patterns = ['compliance']
            else:
                # Fallback: use the team name itself
                patterns = [selected_team_name]
        else:
            # Fallback: try to determine from work item area path
            area_path = work_item.fields.get('System.AreaPath', '')
            if 'accessibility' in area_path.lower():
                patterns = ['accessibility', 'practical law - accessibility', 'practical law accessibility']
            elif 'practical law' in area_path.lower() or 'practicallaw' in area_path.lower():
                patterns = ['practical law', 'practicallaw']
            else:
                # Default fallback patterns - search all accessibility teams
                patterns = ['accessibility', 'practical law - accessibility', 'practical law accessibility']
        
        return patterns
    
    def _generate_title_phrase_combinations(self, title):
        """
        Generate intelligent phrase combinations from a work item title for semantic matching.
        Implements the sophisticated search strategy used in Tkinter GUI:
        1. Full sentence first
        2. Half sentences (progressive fallback)
        3. Word combinations
        4. Cleaned title without verbs/prepositions
        
        Args:
            title (str): The work item title
            
        Returns:
            list: List of phrase combinations for CONTAINS clauses
        """
        try:
            # Clean and normalize the title
            import re
            
            # Remove common prefixes and brackets
            cleaned_title = re.sub(r'^\[.*?\]', '', title).strip()
            cleaned_title = re.sub(r'^\w+:\s*', '', cleaned_title).strip()
            
            # Split into words and remove stop words
            words = re.findall(r'\b\w+\b', cleaned_title.lower())
            
            # Enhanced stop words list (verbs, prepositions, articles, etc.)
            stop_words = {
                'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 
                'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should', 
                'could', 'may', 'might', 'must', 'can', 'to', 'of', 'in', 'on', 'at', 
                'by', 'for', 'with', 'without', 'from', 'upon', 'into', 'onto', 'over', 
                'under', 'through', 'during', 'before', 'after', 'above', 'below', 
                'between', 'among', 'within', 'without', 'against', 'toward', 'towards',
                'get', 'got', 'getting', 'make', 'made', 'making', 'take', 'took', 
                'taking', 'give', 'gave', 'giving', 'go', 'went', 'going', 'come', 
                'came', 'coming', 'see', 'saw', 'seeing', 'know', 'knew', 'knowing',
                'think', 'thought', 'thinking', 'use', 'used', 'using', 'work', 
                'worked', 'working', 'find', 'found', 'finding', 'look', 'looked', 
                'looking', 'want', 'wanted', 'wanting', 'need', 'needed', 'needing',
                'feel', 'felt', 'feeling', 'seem', 'seemed', 'seeming', 'become', 
                'became', 'becoming', 'leave', 'left', 'leaving', 'put', 'putting',
                'tell', 'told', 'telling', 'ask', 'asked', 'asking', 'try', 'tried', 
                'trying', 'turn', 'turned', 'turning', 'move', 'moved', 'moving',
                'play', 'played', 'playing', 'run', 'ran', 'running', 'walk', 
                'walked', 'walking', 'sit', 'sat', 'sitting', 'stand', 'stood', 
                'standing', 'live', 'lived', 'living', 'die', 'died', 'dying'
            }
            
            meaningful_words = [w for w in words if len(w) > 2 and w not in stop_words]
            
            if len(meaningful_words) < 2:
                # If we don't have enough meaningful words, use the original title
                return [cleaned_title]
            
            phrases = []
            
            # Strategy 1: Full cleaned title (highest priority) - like Tkinter GUI
            if len(cleaned_title) > 10:
                phrases.append(cleaned_title)
                            
            # Strategy 2: Half sentences (progressive fallback) - like Tkinter GUI
            # Split title into meaningful chunks and create overlapping phrases
            if len(meaningful_words) >= 4:
                # Create half-sentence phrases by taking chunks of the title
                half_length = len(meaningful_words) // 2
                
                # First half
                first_half = ' '.join(meaningful_words[:half_length + 1])
                if len(first_half) > 8 and first_half not in phrases:
                    phrases.append(first_half)
                
                # Second half
                second_half = ' '.join(meaningful_words[half_length:])
                if len(second_half) > 8 and second_half not in phrases:
                    phrases.append(second_half)
                
                # Middle section (overlapping)
                if len(meaningful_words) >= 6:
                    start_idx = len(meaningful_words) // 3
                    end_idx = start_idx + len(meaningful_words) // 2
                    middle_section = ' '.join(meaningful_words[start_idx:end_idx])
                    if len(middle_section) > 8 and middle_section not in phrases:
                        phrases.append(middle_section)
            
            # Strategy 3: Word combinations (3-4 word phrases) - like Tkinter GUI
            for length in [4, 3]:  # Start with longer phrases
                if len(meaningful_words) >= length:
                    for i in range(len(meaningful_words) - length + 1):
                        phrase_words = meaningful_words[i:i + length]
                        phrase = ' '.join(phrase_words)
                        if len(phrase) > 6 and phrase not in phrases:
                            phrases.append(phrase)
            
            # Strategy 4: Important word pairs (2-word combinations)
            if len(meaningful_words) >= 2:
                for i in range(len(meaningful_words) - 1):
                    pair = f"{meaningful_words[i]} {meaningful_words[i + 1]}"
                    if len(pair) > 5 and pair not in phrases:
                        phrases.append(pair)
            
            # Strategy 5: Skip single words - only use multi-word phrases for better relevance
            # for word in meaningful_words:
            #     if len(word) > 4 and any(indicator in word.lower() for indicator in [
            #         'error', 'fail', 'issue', 'bug', 'problem', 'incorrect', 'missing', 
            #         'filter', 'tree', 'role', 'area', 'practice', 'button', 'dialog', 
            #         'modal', 'focus', 'directed', 'opening', 'heading', 'close', 'open',
            #         'accessibility', 'access', 'keyboard', 'screen', 'reader', 'voice',
            #         'navigation', 'menu', 'dropdown', 'select', 'option', 'choice',
            #         'form', 'input', 'field', 'label', 'text', 'content', 'display',
            #         'show', 'hide', 'visible', 'hidden', 'enable', 'disable', 'active',
            #         'inactive', 'click', 'hover', 'focus', 'blur', 'select', 'deselect'
            #     ]):
            #         if word not in phrases:
            #             phrases.append(word)
            #                         
            # Limit to top 3 most meaningful phrases to avoid query complexity and API limits
            phrases = phrases[:3]
            
            return phrases
            
        except Exception as e:
            logger.error(f"Error generating title phrases: {str(e)}")
            return [title]  # Fallback to original title
    
    def _fallback_basic_search(self, project, work_item):
        """
        Fallback to basic relationship-based search if intelligent search fails.
        
        Args:
            project (str): The project name
            work_item: The work item object
            
        Returns:
            list: List of related work items
        """
        try:
            work_item_client = self.connection.clients.get_work_item_tracking_client()
            work_item_type = work_item.fields.get('System.WorkItemType', '')
            area_path = work_item.fields.get('System.AreaPath', '')

            if work_item_type and area_path:
                wiql_query = f"""
                SELECT [System.Id], [System.Title], [System.WorkItemType], [System.State], 
                       [System.AssignedTo], [System.CreatedBy], [System.CreatedDate], [System.Description]
                FROM WorkItems
                WHERE [System.TeamProject] = '{project}'
                AND [System.Id] != {work_item.id}
                AND [System.WorkItemType] = '{work_item_type}'
                AND [System.AreaPath] UNDER '{area_path}'
                AND [System.State] <> 'Closed'
                AND [System.State] <> 'Removed'
                AND [System.CreatedDate] >= @Today - 1095
                ORDER BY [System.CreatedDate] DESC
                """
            else:
                wiql_query = f"""
                SELECT [System.Id], [System.Title], [System.WorkItemType], [System.State], 
                       [System.AssignedTo], [System.CreatedBy], [System.CreatedDate], [System.Description]
                FROM WorkItems
                WHERE [System.TeamProject] = '{project}'
                AND [System.Id] != {work_item.id}
                AND [System.State] <> 'Closed'
                AND [System.State] <> 'Removed'
                AND [System.CreatedDate] >= @Today - 1095
                ORDER BY [System.CreatedDate] DESC
                """

            # Print WIQL query to terminal for debugging
            print("\n" + "="*80)
            print(f"[QUERY] FALLBACK BASIC WIQL QUERY")
            print("="*80)
            print(wiql_query)
            print("="*80 + "\n")

            wiql = {"query": wiql_query}
            query_result = work_item_client.query_by_wiql(wiql)
            
            if query_result and hasattr(query_result, 'work_items'):
                related_items = []
                for item in query_result.work_items:
                    full_item = work_item_client.get_work_item(item.id)
                    related_items.append(full_item)
                
                logger.info(f"Found {len(related_items)} related work items using fallback search for work item {work_item.id}")
                return related_items
            else:
                return []
                
        except Exception as e:
            logger.error(f"Error in fallback basic search: {str(e)}")
            return []
    
    def query_related_work_items_by_keywords(self, project, work_item):
        """
        Query for work items related by keywords from title and description.
        
        Args:
            project (str): The name of the project.
            work_item: The work item object to extract keywords from.
            
        Returns:
            list: A list of related work item objects based on keyword matching.
        """
        try:
            # Extract keywords from title and description
            keywords = self._extract_keywords_from_work_item(work_item)
            
            if not keywords:
                logger.info(f"No meaningful keywords found for work item {work_item.id}")
                return []
            
            # If we have very few keywords, try a broader search with just the most important ones
            if len(keywords) < 3:
                # Get some basic keywords from title only
                title_text = work_item.fields.get('System.Title', '')
                if title_text:
                    # Extract words that are longer and not in stop words
                    import re
                    words = re.findall(r'\b[a-zA-Z]+\b', title_text.lower())
                    basic_keywords = [word for word in words if len(word) >= 4 and word not in {
                        'the', 'and', 'for', 'with', 'this', 'that', 'from', 'have', 'will', 'been', 'were', 'they', 'been', 'said', 'each', 'which', 'their', 'time', 'would', 'there', 'could', 'other', 'after', 'first', 'well', 'also', 'new', 'want', 'because', 'any', 'these', 'give', 'day', 'most', 'us', 'is', 'are', 'was', 'be', 'to', 'of', 'in', 'on', 'at', 'by', 'or', 'but', 'if', 'as', 'an', 'a', 'it', 'he', 'she', 'we', 'you', 'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'her', 'its', 'our', 'their'
                    }]
                    if basic_keywords:
                        keywords = basic_keywords[:3]
            
            logger.info(f"Searching for work items with keywords: {keywords}")
            
            # Build WIQL query with keyword matching
            keyword_conditions = []
            for keyword in keywords:
                # Search in title and description
                keyword_conditions.append(f"[System.Title] CONTAINS '{keyword}'")
                keyword_conditions.append(f"[System.Description] CONTAINS '{keyword}'")
            
            # Combine conditions with OR
            where_clause = " OR ".join(keyword_conditions)
            
            wiql_query = f"""
            SELECT [System.Id], [System.Title], [System.WorkItemType], [System.State], 
                   [System.AssignedTo], [System.CreatedBy], [System.CreatedDate], [System.Description]
            FROM WorkItems
            WHERE [System.TeamProject] = '{project}'
            AND [System.Id] != {work_item.id}
            AND [System.State] <> 'Closed'
            AND [System.State] <> 'Removed'
            AND ({where_clause})
            ORDER BY [System.CreatedDate] DESC
            """
            
            # Execute the query
            work_item_client = self.connection.clients.get_work_item_tracking_client()
            
            # Use the same format as other methods in the codebase
            wiql = {"query": wiql_query}
            
            try:
                query_result = work_item_client.query_by_wiql(wiql)
            except Exception as query_error:
                if "exceeds the size limit" in str(query_error):
                    # Try a more restrictive query with fewer keywords
                    if len(keywords) > 2:
                        # Use only the first 2 most specific keywords
                        restricted_keywords = keywords[:2]
                        restricted_conditions = []
                        for keyword in restricted_keywords:
                            restricted_conditions.append(f"[System.Title] CONTAINS '{keyword}'")
                            restricted_conditions.append(f"[System.Description] CONTAINS '{keyword}'")
                        
                        restricted_where_clause = " OR ".join(restricted_conditions)
                        restricted_query = f"""
                        SELECT [System.Id], [System.Title], [System.WorkItemType], [System.State], 
                               [System.AssignedTo], [System.CreatedBy], [System.CreatedDate], [System.Description]
                        FROM WorkItems
                        WHERE [System.TeamProject] = '{project}'
                        AND [System.Id] != {work_item.id}
                        AND [System.State] <> 'Closed'
                        AND [System.State] <> 'Removed'
                        AND ({restricted_where_clause})
                        ORDER BY [System.CreatedDate] DESC
                        """
                        
                        wiql = {"query": restricted_query}
                        query_result = work_item_client.query_by_wiql(wiql)
                    else:
                        raise query_error
                else:
                    raise query_error
            
            if query_result and hasattr(query_result, 'work_items'):
                # Limit results to avoid overwhelming the user (max 100 items)
                limited_items = query_result.work_items[:100] if len(query_result.work_items) > 100 else query_result.work_items
                
                related_items = []
                for item in limited_items:
                    # Get the full work item details
                    full_item = work_item_client.get_work_item(item.id)
                    related_items.append(full_item)
                
                logger.info(f"Found {len(related_items)} keyword-related work items for work item {work_item.id}")
                return related_items
            else:
                logger.info(f"No keyword-related work items found for work item {work_item.id}")
                
                # Try a very simple fallback search - just look for work items with similar work item types in the same area
                try:
                    work_item_type = work_item.fields.get('System.WorkItemType', '')
                    area_path = work_item.fields.get('System.AreaPath', '')
                    
                    if work_item_type and area_path:
                        simple_query = f"""
                        SELECT [System.Id], [System.Title], [System.WorkItemType], [System.State], 
                               [System.AssignedTo], [System.CreatedBy], [System.CreatedDate], [System.Description]
                        FROM WorkItems
                        WHERE [System.TeamProject] = '{project}'
                        AND [System.Id] != {work_item.id}
                        AND [System.WorkItemType] = '{work_item_type}'
                        AND [System.AreaPath] UNDER '{area_path}'
                        AND [System.State] <> 'Closed'
                        AND [System.State] <> 'Removed'
                        ORDER BY [System.CreatedDate] DESC
                        """
                        
                        wiql = {"query": simple_query}
                        simple_result = work_item_client.query_by_wiql(wiql)
                        
                        if simple_result and hasattr(simple_result, 'work_items') and simple_result.work_items:
                            # Limit results to avoid overwhelming the user (max 20 items for simple fallback)
                            limited_items = simple_result.work_items[:20] if len(simple_result.work_items) > 20 else simple_result.work_items
                            
                            related_items = []
                            for item in limited_items:
                                full_item = work_item_client.get_work_item(item.id)
                                related_items.append(full_item)
                            return related_items
                        else:
                            return []
                except Exception as fallback_error:
                    return []
                
        except Exception as e:
            logger.error(f"Error querying keyword-related work items for work item {work_item.id}: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
    
    def query_related_work_items_by_title_keywords(self, project, work_item):
        """
        Query for work items related by keywords from title only (optimized single query approach).
        
        Args:
            project (str): The name of the project.
            work_item: The work item object to extract keywords from.
            
        Returns:
            list: A list of related work item objects based on title keyword matching.
        """
        try:
                                    
            # Extract keywords from title only
            title_keywords = self._extract_keywords_from_title_only(work_item)
                        
            if not title_keywords:
                logger.info(f"No meaningful title keywords found for work item {work_item.id}")
                return []
            
            # Build a single optimized WIQL query
            title_text = work_item.fields.get('System.Title', '')
            
            # Extract meaningful phrases from the title (remove common prefixes and numbers)
            import re
            
            # Remove common prefixes like "508:", "[PL CA]", "[Legal Updates]", etc.
            cleaned_title = re.sub(r'^\d+:\s*', '', title_text)  # Remove "508: " prefix
            cleaned_title = re.sub(r'^\[[^\]]+\]\s*', '', cleaned_title)  # Remove "[PL CA]" prefix
            cleaned_title = re.sub(r'^\[[^\]]+\]\s*', '', cleaned_title)  # Remove "[Legal Updates]" prefix
            cleaned_title = re.sub(r'^\[[^\]]+\]\s*', '', cleaned_title)  # Remove "[4.1.2]" prefix
            cleaned_title = re.sub(r'^:\s*', '', cleaned_title)  # Remove any remaining ": " prefix
            cleaned_title = cleaned_title.strip()

            # Helper function to escape single quotes for WIQL
            def escape_wiql_string(text):
                return text.replace("'", "''")
            
            # Create a single optimized search strategy
            search_conditions = []
            
            # Strategy 1: Use the most important keywords (top 3) for broad matching
            top_keywords = title_keywords[:3]  # Limit to top 3 keywords for performance
            for keyword in top_keywords:
                if len(keyword) > 3:  # Only use meaningful keywords
                    escaped_keyword = escape_wiql_string(keyword)
                    search_conditions.append(f"[System.Title] CONTAINS '{escaped_keyword}'")
            
            # Strategy 2: If we have a good cleaned title, also search for it
            if cleaned_title and len(cleaned_title) > 15:
                escaped_title = escape_wiql_string(cleaned_title)
                search_conditions.append(f"[System.Title] CONTAINS '{escaped_title}'")
            
            if not search_conditions:
                                return []
            
            # Combine conditions with OR
            where_clause = " OR ".join(search_conditions)
            
            # Add efficient filters for better performance
            work_item_type = work_item.fields.get('System.WorkItemType', '')
            
            # Build the single optimized query
            wiql_query = f"""
            SELECT [System.Id], [System.Title], [System.WorkItemType], [System.State], 
                   [System.AssignedTo], [System.CreatedBy], [System.CreatedDate], [System.Description]
            FROM WorkItems
            WHERE [System.TeamProject] = '{project}'
            AND [System.Id] != {work_item.id}
            AND ({where_clause})
            AND [System.State] <> 'Removed'
            {f"AND [System.WorkItemType] = '{work_item_type}'" if work_item_type else ""}
            ORDER BY [System.CreatedDate] DESC
            """

            # Also log to the main logger so it appears in logs
            logger.info(f"Title-based WIQL query for work item {work_item.id}:")
            logger.info(wiql_query)
            
            # Execute the single query
            work_item_client = self.connection.clients.get_work_item_tracking_client()
            wiql = {"query": wiql_query}
            
            try:
                query_result = work_item_client.query_by_wiql(wiql)
                                
                if query_result and hasattr(query_result, 'work_items') and query_result.work_items:
                                        
                    # Limit results early to prevent timeout and large response
                    max_results = 50  # Increased limit for better search coverage while maintaining performance
                    limited_work_items = query_result.work_items[:max_results]
                    
                    if len(query_result.work_items) > max_results:
                        limited_work_items = query_result.work_items[:max_results]
                    else:
                        limited_work_items = query_result.work_items
                    
                    # Process results with individual get_work_item calls
                    related_items = []
                    for item in limited_work_items:
                        try:
                            full_item = work_item_client.get_work_item(item.id)
                            related_items.append(full_item)
                        except Exception as item_error:
                            # Continue with other items
                            continue
                    
                    logger.info(f"Found {len(related_items)} title-keyword-related work items for work item {work_item.id}")
                    return related_items
                else:
                    return []
                    
            except Exception as query_error:
                # Don't try multiple fallback queries - just return empty
                return []
                
        except Exception as e:
            logger.error(f"Error querying title-keyword-related work items for work item {work_item.id}: {str(e)}")
            return []
    
    def _extract_keywords_from_title_only(self, work_item):
        """
        Extract meaningful keywords from work item title only (excluding description).
        
        Args:
            work_item: The work item object to extract keywords from.
            
        Returns:
            list: A list of meaningful keywords from title only.
        """
        import re

        # Common stop words to filter out
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
            'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these',
            'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them',
            'my', 'your', 'his', 'her', 'its', 'our', 'their', 'mine', 'yours', 'hers', 'ours', 'theirs'
        }
        
        keywords = set()
        
        # Extract from title only
        if 'System.Title' in work_item.fields and work_item.fields['System.Title']:
            title_text = work_item.fields['System.Title']
            title_keywords = self._extract_keywords_from_text(title_text, stop_words)
            keywords.update(title_keywords)
        else:
            pass
        
        # Filter out very short keywords and common generic terms
        generic_terms = {'bug', 'see', 'field', 'details', 'please', 'steps', 'repro', 'system', 'work', 'item', 'user', 'data', 'test', 'code', 'file', 'page', 'button', 'click', 'form', 'input', 'text', 'value', 'error', 'issue', 'problem', 'fix', 'update', 'change', 'new', 'old', 'good', 'bad', 'high', 'low', 'small', 'large', 'big', 'get', 'set', 'add', 'remove', 'delete', 'create', 'edit', 'save', 'load', 'open', 'close', 'show', 'hide', 'display', 'view', 'list', 'table', 'row', 'column', 'cell', 'link', 'url', 'path', 'name', 'id', 'type', 'state', 'status', 'date', 'time', 'day', 'month', 'year', 'number', 'count', 'size', 'length', 'width', 'height', 'color', 'style', 'design', 'layout', 'menu', 'option', 'choice', 'select', 'check', 'radio', 'box', 'area', 'section', 'part', 'component', 'element', 'object', 'class', 'method', 'function', 'variable', 'parameter', 'argument', 'result', 'output', 'input', 'process', 'handle', 'manage', 'control', 'access', 'permission', 'right', 'role', 'group', 'team', 'project', 'task', 'feature', 'functionality', 'capability', 'requirement', 'specification', 'documentation', 'help', 'support', 'service', 'api', 'interface', 'database', 'server', 'client', 'application', 'software', 'program', 'tool', 'utility', 'plugin', 'extension', 'module', 'library', 'framework', 'platform', 'environment', 'configuration', 'setting', 'option', 'preference', 'default', 'custom', 'standard', 'normal', 'regular', 'special', 'specific', 'general', 'common', 'typical', 'usual', 'expected', 'unexpected', 'correct', 'incorrect', 'valid', 'invalid', 'proper', 'improper', 'right', 'wrong', 'true', 'false', 'yes', 'no', 'ok', 'okay', 'fine', 'well', 'better', 'best', 'worse', 'worst', 'important', 'critical', 'major', 'minor', 'significant', 'insignificant', 'relevant', 'irrelevant', 'useful', 'useless', 'helpful', 'unhelpful', 'clear', 'unclear', 'obvious', 'hidden', 'visible', 'invisible', 'available', 'unavailable', 'enabled', 'disabled', 'active', 'inactive', 'online', 'offline', 'connected', 'disconnected', 'linked', 'unlinked', 'related', 'unrelated', 'associated', 'unassociated', 'matching', 'non-matching', 'similar', 'different', 'same', 'other', 'another', 'additional', 'extra', 'more', 'less', 'most', 'least', 'all', 'none', 'some', 'any', 'every', 'each', 'both', 'either', 'neither', 'first', 'last', 'next', 'previous', 'current', 'recent', 'latest', 'earliest', 'oldest', 'newest', 'recent', 'past', 'future', 'present', 'now', 'then', 'here', 'there', 'where', 'when', 'why', 'how', 'what', 'which', 'who', 'whom', 'whose'}
        
        # Filter out generic terms and short keywords
        filtered_keywords = [kw for kw in keywords if len(kw) >= 4 and kw.lower() not in generic_terms]
                        
        # If we don't have enough specific keywords, fall back to including some important UI terms
        if len(filtered_keywords) < 3:
            # Allow some UI-specific terms that might be important for this search
            ui_important_terms = {'button', 'buttons', 'function', 'selecting', 'alerts', 'westlaw', 'functionality'}
            fallback_keywords = [kw for kw in keywords if len(kw) >= 4 and (kw.lower() not in generic_terms or kw.lower() in ui_important_terms)]
            if len(fallback_keywords) > len(filtered_keywords):
                filtered_keywords = fallback_keywords
            else:
                filtered_keywords = [kw for kw in keywords if len(kw) >= 5]
                        
        # Return top 5 most relevant keywords to reduce query scope
        result = filtered_keywords[:5]
        return result

    def _extract_meaningful_phrases(self, work_item, phrase_length=2):
        """Extract meaningful phrases from work item title for balanced search with configurable phrase length"""
        try:
            title = work_item.fields.get('System.Title', '')
            if not title:
                return []
            
            # Clean and tokenize the title
            import re
            # Remove special characters and split into words
            words = re.findall(r'\b\w+\b', title.lower())
            
            # Filter out common stop words and short words
            stop_words = {
                'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
                'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
                'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those',
                'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them',
                'my', 'your', 'his', 'her', 'its', 'our', 'their', 'mine', 'yours', 'hers', 'ours', 'theirs'
            }
            
            # Filter meaningful words (length > 2, not stop words)
            meaningful_words = [word for word in words if len(word) > 2 and word not in stop_words]
            
            if len(meaningful_words) < phrase_length:
                return []
            
            # Strategy: Generate phrases based on specified phrase_length
            all_phrases = []
            seen = set()
            
            # Generate consecutive phrases of the specified length
            for i in range(len(meaningful_words) - phrase_length + 1):
                phrase_parts = meaningful_words[i:i + phrase_length]
                # Only add if all words are different (avoid "word word" duplicates)
                if len(set(phrase_parts)) == len(phrase_parts):
                    phrase = " ".join(phrase_parts)
                    if phrase not in seen:
                        seen.add(phrase)
                        all_phrases.append(phrase)
            
            # If no phrases found with specified length, try shorter lengths as fallback
            if not all_phrases and phrase_length > 2:
                for fallback_length in range(phrase_length - 1, 1, -1):
                    for i in range(len(meaningful_words) - fallback_length + 1):
                        phrase_parts = meaningful_words[i:i + fallback_length]
                        if len(set(phrase_parts)) == len(phrase_parts):
                            phrase = " ".join(phrase_parts)
                            if phrase not in seen:
                                seen.add(phrase)
                                all_phrases.append(phrase)
                    if all_phrases:  # Stop at first successful fallback
                        break
            
            return all_phrases[:12]
            
        except Exception as e:
            logger.error(f"Error extracting meaningful phrases: {e}")
            return []
    
    def _extract_keywords_from_work_item(self, work_item):
        """
        Extract meaningful keywords from work item title and description.
        
        Args:
            work_item: The work item object to extract keywords from.
            
        Returns:
            list: A list of meaningful keywords.
        """
        import re

        # Common stop words to filter out
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
            'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these',
            'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them',
            'my', 'your', 'his', 'her', 'its', 'our', 'their', 'mine', 'yours', 'hers', 'ours', 'theirs'
        }
        
        keywords = set()
        
        # Extract from title
        if 'System.Title' in work_item.fields and work_item.fields['System.Title']:
            title_text = work_item.fields['System.Title']
            title_keywords = self._extract_keywords_from_text(title_text, stop_words)
            keywords.update(title_keywords)
        else:
            pass
        
        # Extract from description
        if 'System.Description' in work_item.fields and work_item.fields['System.Description']:
            description_text = work_item.fields['System.Description']
            # Remove HTML tags if present
            description_text = re.sub(r'<[^>]+>', ' ', description_text)
            desc_keywords = self._extract_keywords_from_text(description_text, stop_words)
            keywords.update(desc_keywords)
        else:
            pass
        
        # Filter out very short keywords and common generic terms
        generic_terms = {'bug', 'see', 'field', 'details', 'please', 'steps', 'repro', 'system', 'work', 'item', 'user', 'data', 'test', 'code', 'file', 'page', 'button', 'click', 'form', 'input', 'text', 'value', 'error', 'issue', 'problem', 'fix', 'update', 'change', 'new', 'old', 'good', 'bad', 'high', 'low', 'small', 'large', 'big', 'get', 'set', 'add', 'remove', 'delete', 'create', 'edit', 'save', 'load', 'open', 'close', 'show', 'hide', 'display', 'view', 'list', 'table', 'row', 'column', 'cell', 'link', 'url', 'path', 'name', 'id', 'type', 'state', 'status', 'date', 'time', 'day', 'month', 'year', 'number', 'count', 'size', 'length', 'width', 'height', 'color', 'style', 'design', 'layout', 'menu', 'option', 'choice', 'select', 'check', 'radio', 'box', 'area', 'section', 'part', 'component', 'element', 'object', 'class', 'method', 'function', 'variable', 'parameter', 'argument', 'result', 'output', 'input', 'process', 'handle', 'manage', 'control', 'access', 'permission', 'right', 'role', 'group', 'team', 'project', 'task', 'feature', 'functionality', 'capability', 'requirement', 'specification', 'documentation', 'help', 'support', 'service', 'api', 'interface', 'database', 'server', 'client', 'application', 'software', 'program', 'tool', 'utility', 'plugin', 'extension', 'module', 'library', 'framework', 'platform', 'environment', 'configuration', 'setting', 'option', 'preference', 'default', 'custom', 'standard', 'normal', 'regular', 'special', 'specific', 'general', 'common', 'typical', 'usual', 'expected', 'unexpected', 'correct', 'incorrect', 'valid', 'invalid', 'proper', 'improper', 'right', 'wrong', 'true', 'false', 'yes', 'no', 'ok', 'okay', 'fine', 'well', 'better', 'best', 'worse', 'worst', 'important', 'critical', 'major', 'minor', 'significant', 'insignificant', 'relevant', 'irrelevant', 'useful', 'useless', 'helpful', 'unhelpful', 'clear', 'unclear', 'obvious', 'hidden', 'visible', 'invisible', 'available', 'unavailable', 'enabled', 'disabled', 'active', 'inactive', 'online', 'offline', 'connected', 'disconnected', 'linked', 'unlinked', 'related', 'unrelated', 'associated', 'unassociated', 'matching', 'non-matching', 'similar', 'different', 'same', 'other', 'another', 'additional', 'extra', 'more', 'less', 'most', 'least', 'all', 'none', 'some', 'any', 'every', 'each', 'both', 'either', 'neither', 'first', 'last', 'next', 'previous', 'current', 'recent', 'latest', 'earliest', 'oldest', 'newest', 'recent', 'past', 'future', 'present', 'now', 'then', 'here', 'there', 'where', 'when', 'why', 'how', 'what', 'which', 'who', 'whom', 'whose'}
        
        # Filter out generic terms and short keywords
        filtered_keywords = [kw for kw in keywords if len(kw) >= 4 and kw.lower() not in generic_terms]
                        
        # If we don't have enough specific keywords, fall back to longer common terms
        if len(filtered_keywords) < 3:
            filtered_keywords = [kw for kw in keywords if len(kw) >= 5]
                    
        # Return top 5 most relevant keywords to reduce query scope
        result = filtered_keywords[:5]
        return result
    
    def _extract_keywords_from_text(self, text, stop_words):
        """
        Extract keywords from text by splitting and filtering.
        
        Args:
            text (str): The text to extract keywords from.
            stop_words (set): Set of stop words to filter out.
            
        Returns:
            list: List of extracted keywords.
        """
        import re
        
        if not text:
            return []
        
        # Convert to lowercase and split into words
        words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
        
        # Filter out stop words and short words
        keywords = [word for word in words if word not in stop_words and len(word) >= 3]
        
        # Remove duplicates while preserving order
        seen = set()
        unique_keywords = []
        for keyword in keywords:
            if keyword not in seen:
                seen.add(keyword)
                unique_keywords.append(keyword)
        
        return unique_keywords
    
    def print_teams(self, teams):
        """
        Print details of teams.
        
        Args:
            teams: List of team objects to print details for.
        """
        if not teams:
            print("No teams found.")
            return
        
        print(f"\n=== Teams ({len(teams)} found) ===")
        for i, team in enumerate(teams, 1):
            print(f"{i}. {team.name}")
            if hasattr(team, 'description') and team.description:
                print(f"   Description: {team.description}")
            if hasattr(team, 'id'):
                print(f"   ID: {team.id}")
            print()

    def get_available_area_paths(self, project, team=None):
        """
        Get available area paths for a project or team.
        
        Args:
            project (str): The name of the project.
            team (str, optional): The name of the team to filter by.
            
        Returns:
            list: A list of available area paths.
        """
        try:
            logger.info(f"Getting available area paths for project '{project}'" + (f" and team '{team}'" if team else ""))
            
            # Build WIQL query to find all area paths
            if team:
                # Try to find area paths that are under the team area path
                wiql_query = f"""
                SELECT DISTINCT [System.AreaPath]
                FROM workitems
                WHERE [System.TeamProject] = '{project}'
                AND [System.AreaPath] UNDER '{project}\\{team}'
                ORDER BY [System.AreaPath]
                """
            else:
                # Get all area paths in the project
                wiql_query = f"""
                SELECT DISTINCT [System.AreaPath]
                FROM workitems
                WHERE [System.TeamProject] = '{project}'
                ORDER BY [System.AreaPath]
                """
            
            logger.info(f"Executing area path discovery query: {wiql_query}")
            
            # Execute the query
            wiql = {"query": wiql_query}
            query_result = self.work_item_client.query_by_wiql(wiql).work_items
            
            if not query_result:
                logger.info(f"No area paths found for project '{project}'" + (f" and team '{team}'" if team else ""))
                return []
            
            # Extract area paths from the results
            area_paths = []
            for res in query_result:
                try:
                    # The result should have the area path in a field
                    area_path = res.fields.get('System.AreaPath', '') if hasattr(res, 'fields') else str(res)
                    if area_path and area_path not in area_paths:
                        area_paths.append(area_path)
                except Exception as e:
                    logger.warning(f"Could not extract area path from result {res}: {e}")
                    continue
            
            logger.info(f"Found {len(area_paths)} area paths for project '{project}'" + (f" and team '{team}'" if team else ""))
            return area_paths
            
        except Exception as e:
            logger.error(f"Error getting available area paths: {e}")
            return []

    def load_team_area_path_config(self):
        """
        Load team area path configuration from config file.
        
        Returns:
            dict: Configuration dictionary with team mappings and settings.
        """
        try:
            # Look for config file in multiple locations
            config_paths = [
                "config/team_area_paths.json",
                "../config/team_area_paths.json",
                "../../config/team_area_paths.json"
            ]
            
            config = None
            for config_path in config_paths:
                if os.path.exists(config_path):
                    try:
                        with open(config_path, 'r') as f:
                            config = json.load(f)
                        logger.info(f"Loaded team area path config from: {config_path}")
                        break
                    except Exception as e:
                        logger.warning(f"Could not load config from {config_path}: {e}")
                        continue
            
            if not config:
                logger.warning("No team area path config found, using defaults")
                config = {
                    "team_area_path_mappings": {},
                    "area_path_patterns": {
                        "team_name_in_path": True,
                        "case_sensitive": False,
                        "partial_matching": True
                    },
                    "fallback_strategies": {
                        "use_team_backlog": True,
                        "use_constructed_paths": True,
                        "use_manual_mapping": True,
                        "use_project_query": True
                    }
                }
            
            return config
            
        except Exception as e:
            logger.error(f"Error loading team area path config: {e}")
            return {}

    def get_team_area_path_mappings(self):
        """
        Get team area path mappings from configuration.
        
        Returns:
            dict: Dictionary mapping team names to area paths.
        """
        config = self.load_team_area_path_config()
        return config.get("team_area_path_mappings", {})

    def get_team_backlog_items(self, project, team, work_item_type=None, state=None, limit=50):
        """
        Get work items directly from team backlog (most reliable method).
        Note: Team backlogs typically only contain "Active" work items.
        For other states, we should use area path or project-wide queries.
        """
        try:
            logger.info(f"Getting team backlog items for team '{team}' in project '{project}'")
            
            # Check if we're filtering by a non-active state or "All" states
            if state is None or (state and state.lower() not in ['active', 'new', 'in progress']):
                if state is None:
                    logger.info("State filter 'All' requested, but team backlogs typically only contain active items.")
                else:
                    logger.info(f"State filter '{state}' requested, but team backlogs typically only contain active items.")
                logger.info("Skipping team backlog query and will use area path or project-wide query instead.")
                return []  # Return empty to trigger fallback to other strategies
            
            # Get the work client for team context
            work_client = self.connection.clients.get_work_client()
            
            # Get team backlog
            team_backlog = work_client.get_backlog(project, team)
            if not team_backlog:
                logger.warning(f"No backlog found for team '{team}'")
                return []
            
            logger.info(f"Found team backlog: {team_backlog}")
            
            # Get work items from the backlog
            backlog_items = work_client.get_backlog_work_items(project, team, team_backlog.id)
            if not backlog_items:
                logger.info(f"No work items found in team '{team}' backlog")
                return []
            
            logger.info(f"Found {len(backlog_items)} items in team '{team}' backlog")
            
            # Debug: Show states found in backlog items
            if state:
                logger.info(f"Filtering by state: '{state}'")
                found_states = set()
                for item in backlog_items[:10]:  # Check first 10 items for debugging
                    try:
                        work_item = self.work_item_client.get_work_item(int(item.id))
                        item_state = work_item.fields.get('System.State', 'Unknown')
                        found_states.add(item_state)
                    except:
                        pass
                logger.info(f"States found in backlog items: {sorted(found_states)}")
            
            # Filter by work item type and state if specified
            filtered_items = []
            for item in backlog_items:
                try:
                    # Get the full work item details
                    work_item = self.work_item_client.get_work_item(int(item.id))
                    
                    # Apply filters
                    if work_item_type and work_item.fields.get('System.WorkItemType') != work_item_type:
                        continue
                    
                    if state and work_item.fields.get('System.State') != state:
                        logger.debug(f"Filtering out work item {work_item.id}: state '{work_item.fields.get('System.State')}' != '{state}'")
                        continue
                    
                    filtered_items.append(work_item)
                    
                    # Check limit
                    if len(filtered_items) >= limit:
                        break
                        
                except Exception as e:
                    logger.warning(f"Could not get work item {item.id}: {e}")
                    continue
            
            logger.info(f"Retrieved {len(filtered_items)} filtered work items for team '{team}' from backlog")
            return filtered_items
            
        except Exception as e:
            logger.error(f"Error getting team backlog items: {e}")
            return []

    def get_team_work_items_enhanced(self, project, team, work_item_type=None, state=None, limit=50):
        """
        Enhanced method to get team work items using team-specific queries only.
        Uses area path queries and manual mappings, never falls back to project-wide queries.
        """
        import time
        start_time = time.time()
        
        # Validate inputs
        if not project or not project.strip():
            logger.error("Project name is required")
            return []
        
        if not team or not team.strip():
            logger.error("Team name is required")
            return []
        
        # Clean and validate team name
        team = team.strip()
        project = project.strip()
        
        logger.info(f"Getting work items for team '{team}' in project '{project}' using team-specific queries only")
        
        # Pre-check query size to determine if we need parallel processing
        estimated_count = self._estimate_query_size(project, team, work_item_type, state)
        logger.info(f"Estimated query size: {estimated_count} items")
        
        # If estimated count is high, use parallel processing with team-specific queries
        if estimated_count > 2000:
            logger.info(f"Large result set detected ({estimated_count} items), using parallel team-specific processing")
            return self._get_work_items_parallel(project, team, work_item_type, state, limit, estimated_count)
        
        # Strategy 1: Team area path query (most reliable for team-specific data)
        logger.info("Strategy 1: Trying team area path query...")
        try:
            area_path_items = self.get_team_work_items_by_area_path(project, team, work_item_type, state, limit)
            if area_path_items:
                logger.info(f"[SUCCESS] Successfully retrieved {len(area_path_items)} items using team area path")
                end_time = time.time()
                total_time = end_time - start_time
                logger.info(f"[SUCCESS] Retrieved {len(area_path_items)} work items for team '{team}' in {total_time:.2f} seconds")
                return area_path_items
            else:
                logger.info("[WARNING] Team area path query returned no items, trying next strategy")
        except Exception as e:
            logger.warning(f"Team area path query failed: {e}, trying next strategy")
        
        # Strategy 2: Manual area path mapping (fallback for teams without configured area paths)
        logger.info("Strategy 2: Trying manual area path mapping...")
        try:
            manual_items = self.get_team_work_items_by_manual_mapping(project, team, work_item_type, state, limit)
            if manual_items:
                logger.info(f"[SUCCESS] Successfully retrieved {len(manual_items)} items using manual area path mapping")
                end_time = time.time()
                total_time = end_time - start_time
                logger.info(f"[SUCCESS] Retrieved {len(manual_items)} work items for team '{team}' in {total_time:.2f} seconds")
                return manual_items
            else:
                logger.info("[WARNING] Manual area path mapping returned no items")
        except Exception as e:
            logger.warning(f"Manual area path mapping failed: {e}")
        
        # Strategy 3: Enhanced team-specific query with multiple area path attempts
        logger.info("Strategy 3: Trying enhanced team-specific query...")
        try:
            enhanced_items = self._get_team_work_items_enhanced_fallback(project, team, work_item_type, state, limit)
            if enhanced_items:
                logger.info(f"[SUCCESS] Successfully retrieved {len(enhanced_items)} items using enhanced team-specific query")
                end_time = time.time()
                total_time = end_time - start_time
                logger.info(f"[SUCCESS] Retrieved {len(enhanced_items)} work items for team '{team}' in {total_time:.2f} seconds")
                return enhanced_items
            else:
                logger.info("[WARNING] Enhanced team-specific query returned no items")
        except Exception as e:
            logger.warning(f"Enhanced team-specific query failed: {e}")
        
        end_time = time.time()
        total_time = end_time - start_time
        logger.warning(f"All team-specific strategies failed for team '{team}' after {total_time:.2f} seconds")
        logger.warning("No project-wide fallback available - team-specific queries only")
        return []

    def _get_team_work_items_enhanced_fallback(self, project, team, work_item_type=None, state=None, limit=50):
        """
        Enhanced team-specific query fallback that tries multiple area path patterns
        and team-specific indicators without using project-wide queries.
        """
        try:
            logger.info(f"Using enhanced team-specific fallback for team '{team}'")
            
            # Try multiple area path patterns for the team (backslash only)
            area_path_patterns = [
                f"{project}\\{team}",
                team,
                f"{project}\\{team.replace(' - ', ' ')}",
                f"{project}\\{team.replace(' - ', '-')}",
                f"{project}\\{team.replace(' ', '')}",
            ]
            
            # Load area path patterns from generated mapping file
            try:
                import json
                import os
                mapping_file = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'team_area_paths.json')
                if os.path.exists(mapping_file):
                    with open(mapping_file, 'r', encoding='utf-8') as f:
                        mapping_data = json.load(f)
                        mappings = mapping_data.get('mappings', {})
                        if team in mappings and mappings[team].get('verified', False):
                            correct_area_path = mappings[team]['area_path']
                            area_path_patterns.insert(0, correct_area_path)
            except Exception as e:
                logger.warning(f"Error loading area path mapping for team '{team}': {e}")
            
            logger.info(f"Trying {len(area_path_patterns)} area path patterns for team '{team}'")
            
            for pattern in area_path_patterns:
                try:
                    logger.info(f"Testing area path pattern: '{pattern}'")
                    
                    # Build WIQL query for this area path pattern
                    wiql_query = f"""
                    SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType], [System.AssignedTo], [System.CreatedDate]
                    FROM workitems
                    WHERE [System.TeamProject] = '{project}'
                    AND [System.AreaPath] UNDER '{pattern}'
                    """
                    
                    if work_item_type:
                        wiql_query += f" AND [System.WorkItemType] = '{work_item_type}'"
                    
                    if state:
                        wiql_query += f" AND [System.State] = '{state}'"
                    
                    wiql_query += f" ORDER BY [System.CreatedDate] DESC"
                    
                    logger.info(f"Executing enhanced team query: {wiql_query}")
                    
                    wiql = {"query": wiql_query}
                    query_result = self.work_item_client.query_by_wiql(wiql).work_items
                    
                    if query_result:
                        # Limit results and get full work items
                        query_result = query_result[:limit]
                        work_items = self.get_work_items_batch([int(res.id) for res in query_result])
                        
                        logger.info(f"[SUCCESS] Found {len(work_items)} work items using area path pattern '{pattern}'")
                        return work_items
                    else:
                        logger.info(f"[INFO] Area path pattern '{pattern}' returned no work items")
                        
                except Exception as e:
                    logger.info(f"[INFO] Area path pattern '{pattern}' failed: {e}")
                    continue
            
            # If no area path patterns worked, try team-specific filtering by other indicators
            logger.info("No area path patterns worked, trying team-specific filtering by other indicators")
            
            # Try to find work items that are clearly team-related
            team_indicators_query = f"""
            SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType], [System.AssignedTo], [System.CreatedDate]
            FROM workitems
            WHERE [System.TeamProject] = '{project}'
            AND [System.AreaPath] CONTAINS '{team}'
            """
            
            if work_item_type:
                team_indicators_query += f" AND [System.WorkItemType] = '{work_item_type}'"
            
            if state:
                team_indicators_query += f" AND [System.State] = '{state}'"
            
            team_indicators_query += f" ORDER BY [System.CreatedDate] DESC"
            
            logger.info(f"Executing team indicators query: {team_indicators_query}")
            
            wiql = {"query": team_indicators_query}
            query_result = self.work_item_client.query_by_wiql(wiql).work_items
            
            if query_result:
                # Limit results and get full work items
                query_result = query_result[:limit]
                work_items = self.get_work_items_batch([int(res.id) for res in query_result])
                
                logger.info(f"[SUCCESS] Found {len(work_items)} work items using team indicators")
                return work_items
            else:
                logger.info("[WARNING] Team indicators query returned no work items")
                return []
                
        except Exception as e:
            logger.error(f"Error in enhanced team-specific fallback: {e}")
            return []

    def _estimate_query_size(self, project, team, work_item_type=None, state=None):
        """
        Estimate the number of work items that would be returned by a team-specific query.
        This helps determine if we need parallel processing.
        """
        try:
            # Try to estimate using team area path patterns (backslash only)
            area_path_patterns = [
                f"{project}\\{team}",
                team,
                f"{project}\\{team.replace(' - ', ' ')}",
            ]
            
            for pattern in area_path_patterns:
                try:
                    # Build a count-only team-specific query to estimate size
                    wiql_query = f"""
                    SELECT [System.Id]
                    FROM workitems
                    WHERE [System.TeamProject] = '{project}'
                    AND [System.AreaPath] UNDER '{pattern}'
                    """
                    
                    if work_item_type:
                        wiql_query += f" AND [System.WorkItemType] = '{work_item_type}'"
                    
                    if state:
                        wiql_query += f" AND [System.State] = '{state}'"
                    else:
                        # For "All" state, use recent date filter to get a reasonable estimate
                        from datetime import datetime, timedelta
                        recent_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
                        wiql_query += f" AND [System.CreatedDate] >= '{recent_date}'"
                    
                    wiql_query += f" ORDER BY [System.CreatedDate] DESC"
                    
                    logger.info(f"Executing team-specific count estimation query (pattern: {pattern}): {wiql_query}")
                    
                    wiql = {"query": wiql_query}
                    query_result = self.work_item_client.query_by_wiql(wiql).work_items
                    
                    if query_result:
                        estimated_count = len(query_result)
                        logger.info(f"Team-specific query estimation returned {estimated_count} items using pattern '{pattern}'")
                        return estimated_count
                    else:
                        logger.info(f"Pattern '{pattern}' returned no items, trying next pattern")
                        continue
                        
                except Exception as e:
                    logger.info(f"Pattern '{pattern}' failed: {e}, trying next pattern")
                    continue
            
            # If no area path patterns worked, try team indicators query
            logger.info("No area path patterns worked, trying team indicators estimation")
            
            team_indicators_query = f"""
            SELECT [System.Id]
            FROM workitems
            WHERE [System.TeamProject] = '{project}'
            AND [System.AreaPath] CONTAINS '{team}'
            """
            
            if work_item_type:
                team_indicators_query += f" AND [System.WorkItemType] = '{work_item_type}'"
            
            if state:
                team_indicators_query += f" AND [System.State] = '{state}'"
            else:
                from datetime import datetime, timedelta
                recent_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
                team_indicators_query += f" AND [System.CreatedDate] >= '{recent_date}'"
            
            team_indicators_query += f" ORDER BY [System.CreatedDate] DESC"
            
            logger.info(f"Executing team indicators estimation query: {team_indicators_query}")
            
            wiql = {"query": team_indicators_query}
            query_result = self.work_item_client.query_by_wiql(wiql).work_items
            
            estimated_count = len(query_result) if query_result else 0
            logger.info(f"Team indicators query estimation returned {estimated_count} items")
            
            return estimated_count
            
        except Exception as e:
            logger.warning(f"Error estimating team-specific query size: {e}")
            # Return a conservative estimate if we can't determine the size
            return 1000

    def _get_work_items_parallel(self, project, team, work_item_type=None, state=None, limit=50, estimated_count=2000):
        """
        Get work items using parallel processing for large result sets with team-specific queries only.
        Splits team-specific queries into multiple smaller queries and processes them in parallel.
        """
        import concurrent.futures
        import threading
        from datetime import datetime, timedelta
        
        try:
            logger.info(f"Starting parallel processing for {estimated_count} estimated items using team-specific queries only")
            
            # Determine how many parallel queries we need
            max_items_per_query = 10000  # Keep each query under 10000 items
            num_queries = min(5, (estimated_count // max_items_per_query) + 1)  # Max 5 parallel queries
            
            logger.info(f"Will split into {num_queries} parallel queries with max {max_items_per_query} items each")
            
            # Get team area path patterns for parallel processing (backslash only)
            area_path_patterns = [
                f"{project}\\{team}",
                team,
                f"{project}\\{team.replace(' - ', ' ')}",
                f"{project}\\{team.replace(' - ', '-')}",
            ]
            
            # Load area path patterns from generated mapping file
            try:
                import json
                import os
                mapping_file = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'team_area_paths.json')
                if os.path.exists(mapping_file):
                    with open(mapping_file, 'r', encoding='utf-8') as f:
                        mapping_data = json.load(f)
                        mappings = mapping_data.get('mappings', {})
                        if team in mappings and mappings[team].get('verified', False):
                            correct_area_path = mappings[team]['area_path']
                            area_path_patterns.insert(0, correct_area_path)
            except Exception as e:
                logger.warning(f"Error loading area path mapping for team '{team}': {e}")
            
            # Create date ranges for parallel queries
            if state is None:
                # For "All" state, split by time periods
                end_date = datetime.now()
                start_date = end_date - timedelta(days=90)
                date_ranges = []
                
                days_per_query = 90 // num_queries
                for i in range(num_queries):
                    query_start = start_date + timedelta(days=i * days_per_query)
                    query_end = start_date + timedelta(days=(i + 1) * days_per_query)
                    if i == num_queries - 1:  # Last query gets remaining days
                        query_end = end_date
                    date_ranges.append((query_start.strftime('%Y-%m-%d'), query_end.strftime('%Y-%m-%d')))
            else:
                # For specific state, split by work item type or use different approaches
                date_ranges = [(None, None)] * num_queries
            
            # Function to execute a single parallel team-specific query
            def execute_parallel_team_query(query_index, date_range, area_pattern):
                try:
                    start_date, end_date = date_range
                    
                    # Build team-specific WIQL query
                    wiql_query = f"""
                    SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType], [System.AssignedTo], [System.CreatedDate]
                    FROM workitems
                    WHERE [System.TeamProject] = '{project}'
                    AND [System.AreaPath] UNDER '{area_pattern}'
                    """
                    
                    if work_item_type:
                        wiql_query += f" AND [System.WorkItemType] = '{work_item_type}'"
                    
                    if state:
                        wiql_query += f" AND [System.State] = '{state}'"
                    
                    if start_date and end_date:
                        wiql_query += f" AND [System.CreatedDate] >= '{start_date}' AND [System.CreatedDate] < '{end_date}'"
                    
                    wiql_query += f" ORDER BY [System.CreatedDate] DESC"
                    
                    logger.info(f"Parallel team query {query_index + 1} (area: {area_pattern}): {wiql_query}")
                    
                    wiql = {"query": wiql_query}
                    query_result = self.work_item_client.query_by_wiql(wiql).work_items
                    
                    if not query_result:
                        logger.info(f"Parallel team query {query_index + 1} returned no items")
                        return []
                    
                    # Limit results per query
                    query_result = query_result[:max_items_per_query]
                    
                    # Get full work items
                    work_items = self.get_work_items_batch([int(res.id) for res in query_result])
                    
                    logger.info(f"Parallel team query {query_index + 1} found {len(work_items)} team-specific items")
                    return work_items
                    
                except Exception as e:
                    logger.error(f"Error in parallel team query {query_index + 1}: {e}")
                    return []
            
            # Execute parallel team-specific queries
            all_team_items = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_queries) as executor:
                # Submit all parallel queries using different area path patterns
                future_to_query = {}
                for i in range(num_queries):
                    area_pattern = area_path_patterns[i % len(area_path_patterns)]
                    future = executor.submit(execute_parallel_team_query, i, date_ranges[i], area_pattern)
                    future_to_query[future] = i
                
                # Collect results as they complete
                for future in concurrent.futures.as_completed(future_to_query):
                    query_index = future_to_query[future]
                    try:
                        result = future.result()
                        all_team_items.extend(result)
                        logger.info(f"Completed parallel team query {query_index + 1}, total items so far: {len(all_team_items)}")
                    except Exception as e:
                        logger.error(f"Parallel team query {query_index + 1} failed: {e}")
            
            # Remove duplicates and limit results
            seen_ids = set()
            unique_items = []
            for item in all_team_items:
                item_id = item.id
                if item_id not in seen_ids:
                    seen_ids.add(item_id)
                    unique_items.append(item)
                    if len(unique_items) >= limit:
                        break
            
            logger.info(f"Parallel team processing completed: {len(unique_items)} unique team-specific items")
            return unique_items
            
        except Exception as e:
            logger.error(f"Error in parallel team processing: {e}")
            # Fallback to enhanced team-specific query
            logger.info("Falling back to enhanced team-specific query")
            return self._get_team_work_items_enhanced_fallback(project, team, work_item_type, state, limit)

    def _is_team_related(self, work_item, team):
        """
        Check if a work item is related to the specified team.
        """
        try:
            # Check area path for team name (case insensitive)
            area_path = work_item.fields.get('System.AreaPath', '')
            if team.lower() in area_path.lower():
                return True
            
            # Check assigned to field for team members
            assigned_to = work_item.fields.get('System.AssignedTo', '')
            if assigned_to and team.lower() in str(assigned_to).lower():
                return True
            
            # Check tags for team indicators
            tags = work_item.fields.get('System.Tags', '')
            if tags and team.lower() in str(tags).lower():
                return True
            
            # Check title for team indicators
            title = work_item.fields.get('System.Title', '')
            if title and team.lower() in title.lower():
                return True
            
            # Check iteration path for team indicators
            iteration_path = work_item.fields.get('System.IterationPath', '')
            if iteration_path and team.lower() in iteration_path.lower():
                return True
            
            return False
            
        except Exception as e:
            logger.warning(f"Error checking team relation: {e}")
            return False

    def get_team_work_items_by_area_path(self, project, team, work_item_type=None, state=None, limit=50):
        """
        Get team work items using configured area path.
        """
        try:
            # Get team's configured area path
            core_client = self.connection.clients.get_core_client()
            team_info = core_client.get_team(project, team)
            
            area_path = None
            if hasattr(team_info, 'default_area_path') and team_info.default_area_path:
                area_path = team_info.default_area_path
                logger.info(f"Using team's configured area path: {area_path}")
            else:
                logger.warning(f"No configured area path found for team '{team}' - skipping area path query")
                return []
            
            # Query work items in the area path
            wiql_query = f"""
            SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType], [System.AssignedTo], [System.CreatedDate]
            FROM workitems
            WHERE [System.TeamProject] = '{project}'
            AND [System.AreaPath] UNDER '{area_path}'
            """
            
            if work_item_type:
                wiql_query += f" AND [System.WorkItemType] = '{work_item_type}'"
            
            if state:
                wiql_query += f" AND [System.State] = '{state}'"
            
            wiql_query += f" ORDER BY [System.CreatedDate] DESC"
            
            logger.info(f"Executing area path WIQL query: {wiql_query}")
            
            wiql = {"query": wiql_query}
            query_result = self.work_item_client.query_by_wiql(wiql).work_items
            
            if not query_result:
                logger.info(f"No work items found in area path '{area_path}'")
                return []
            
            # Limit results and get full work items using batch processing
            query_result = query_result[:limit]
            work_items = self.get_work_items_batch([int(res.id) for res in query_result])
            
            logger.info(f"Retrieved {len(work_items)} work items from area path '{area_path}'")
            return work_items
            
        except Exception as e:
            logger.error(f"Error getting team work items by area path: {e}")
            return []

    def get_team_work_items_by_manual_mapping(self, project, team, work_item_type=None, state=None, limit=50):
        """
        Get team work items using manual area path mapping.
        This provides a fallback when teams don't have configured area paths.
        """
        try:
            # Get manual area path mappings from configuration
            manual_mappings = self.get_team_area_path_mappings()
            
            # Check if we have a manual mapping for this team
            if team in manual_mappings:
                area_paths = manual_mappings[team]
                logger.info(f"Using manual area path mapping for team '{team}': {area_paths}")
                
                # Try different area path formats
                area_path_formats = []
                
                # Format 1: Direct area path from config
                for area_path in area_paths:
                    area_path_formats.append(area_path)
                
                # Format 2: With project prefix (backslash only)
                for area_path in area_paths:
                    area_path_formats.append(f"{project}\\{area_path}")
                
                # Format 3: With project prefix and team name (backslash only)
                for area_path in area_paths:
                    # Split on backslash and get the last part
                    if '\\' in area_path:
                        last_part = area_path.split('\\')[-1]
                    else:
                        last_part = area_path
                    area_path_formats.append(f"{project}\\{team}\\{last_part}")
                
                # Format 4: Just team name (common pattern)
                area_path_formats.append(team)
                area_path_formats.append(f"{project}\\{team}")
                
                logger.info(f"Trying {len(area_path_formats)} different area path formats for team '{team}'")
                
                # Try each area path format until we find one with work items
                for area_path in area_path_formats:
                    try:
                        logger.info(f"Trying area path format: '{area_path}'")
                        
                        # Query work items in the manual area path
                        wiql_query = f"""
                        SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType], [System.AssignedTo], [System.CreatedDate]
                        FROM workitems
                        WHERE [System.TeamProject] = '{project}'
                        AND [System.AreaPath] UNDER '{area_path}'
                        """
                        
                        if work_item_type:
                            wiql_query += f" AND [System.WorkItemType] = '{work_item_type}'"
                        
                        if state:
                            wiql_query += f" AND [System.State] = '{state}'"
                        
                        wiql_query += f" ORDER BY [System.CreatedDate] DESC"
                        
                        logger.info(f"Executing manual mapping WIQL query: {wiql_query}")
                        
                        wiql = {"query": wiql_query}
                        query_result = self.work_item_client.query_by_wiql(wiql).work_items
                        
                        if query_result:
                            # Limit results and get full work items
                            query_result = query_result[:limit]
                            work_items = self.get_work_items_batch([int(res.id) for res in query_result])
                            
                            logger.info(f"[SUCCESS] Successfully retrieved {len(work_items)} work items from manual area path '{area_path}'")
                            return work_items
                        else:
                            logger.info(f"[ERROR] No work items found in manual area path '{area_path}', trying next format...")
                            continue
                            
                    except Exception as e:
                        logger.warning(f"Error querying manual area path '{area_path}': {e}")
                        continue
                
                logger.info(f"All manual area path formats for team '{team}' returned no work items")
                return []
            
            logger.info(f"No manual area path mapping found for team '{team}'")
            return []
            
        except Exception as e:
            logger.error(f"Error getting team work items by manual mapping: {e}")
            return []

    def get_team_work_items_by_project_query(self, project, team, work_item_type=None, state=None, limit=50):
        """
        Get team work items using project-wide query with team filtering.
        This is the last resort when other methods fail.
        """
        try:
            logger.info(f"Using project-wide query with team filtering for team '{team}'")
            
            # Add a reasonable limit to prevent VS402337 error
            # Use a much smaller limit for "All" state queries to avoid hitting the 20,000 limit
            if state is None:
                max_limit = 25  # Very small limit for "All" state to prevent VS402337
            else:
                max_limit = min(limit * 10, 10000)  # Cap at 10000 items for specific state queries
            
            # Build a project-wide query with TOP clause
            wiql_query = f"""
            SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType], [System.AssignedTo], [System.CreatedDate]
            FROM workitems
            WHERE [System.TeamProject] = '{project}'
            """
            
            if work_item_type:
                wiql_query += f" AND [System.WorkItemType] = '{work_item_type}'"
            
            if state:
                wiql_query += f" AND [System.State] = '{state}'"
            else:
                # For "All" state, we'll use a different approach - query the most common states individually
                # This avoids the VS402337 error by not trying to get all states at once
                logger.info("'All' state requested - will query most common states individually to avoid VS402337 error")
                return self.get_all_states_combined(project, team, work_item_type, limit)
            
            wiql_query += f" ORDER BY [System.CreatedDate] DESC"
            
            logger.info(f"Executing project-wide WIQL query (limited to {max_limit} items): {wiql_query}")
            
            wiql = {"query": wiql_query}
            query_result = self.work_item_client.query_by_wiql(wiql).work_items
            
            if not query_result:
                logger.info(f"No work items found in project '{project}'")
                return []
            
            # Apply limit to prevent VS402337 error
            if len(query_result) > max_limit:
                logger.info(f"Query returned {len(query_result)} items, limiting to {max_limit} to prevent VS402337 error")
                query_result = query_result[:max_limit]
            
            logger.info(f"Found {len(query_result)} total work items, filtering by team indicators...")
            
            # Get all work items in batch for better performance
            all_work_items = self.get_work_items_batch([int(res.id) for res in query_result])
            
            # Filter by team (this is less reliable but provides a fallback)
            # Look for team-related indicators in the work items
            team_related_items = []
            team_indicators = []
            
            for work_item in all_work_items:
                # Check if work item is team-related
                is_team_related = False
                indicator_reason = ""
                
                # Check area path for team name
                area_path = work_item.fields.get('System.AreaPath', '')
                if team.lower() in area_path.lower():
                    is_team_related = True
                    indicator_reason = f"Area path contains team name: {area_path}"
                
                # Check assigned to field for team members
                assigned_to = work_item.fields.get('System.AssignedTo', '')
                if assigned_to and team.lower() in str(assigned_to).lower():
                    is_team_related = True
                    indicator_reason = f"Assigned to contains team name: {assigned_to}"
                
                # Check tags for team indicators
                tags = work_item.fields.get('System.Tags', '')
                if tags and team.lower() in str(tags).lower():
                    is_team_related = True
                    indicator_reason = f"Tags contain team name: {tags}"
                
                # Check title for team indicators
                title = work_item.fields.get('System.Title', '')
                if title and team.lower() in title.lower():
                    is_team_related = True
                    indicator_reason = f"Title contains team name: {title[:50]}..."
                
                if is_team_related:
                    team_related_items.append(work_item)
                    team_indicators.append(indicator_reason)
                    
                    # Check limit
                    if len(team_related_items) >= limit:
                        break
            
            if team_related_items:
                logger.info(f"[SUCCESS] Found {len(team_related_items)} team-related work items using project-wide query")
                logger.info("Team indicators found:")
                for i, (item, indicator) in enumerate(zip(team_related_items[:5], team_indicators[:5]), 1):
                    logger.info(f"  {i}. {indicator}")
                if len(team_related_items) > 5:
                    logger.info(f"  ... and {len(team_related_items) - 5} more")
            else:
                logger.warning(f"[WARNING] No team-related work items found using project-wide query")
                logger.info("This means the team filtering is not working properly")
                logger.info("Consider:")
                logger.info("  1. Configuring team area paths in Azure DevOps")
                logger.info("  2. Adding manual area path mappings")
                logger.info("  3. Ensuring team names match exactly")
            
            return team_related_items
            
        except Exception as e:
            logger.error(f"Error getting team work items by project query: {e}")
            return []
    
    def filter_work_items_by_team(self, work_items, team):
        """
        Filter work items by team indicators.
        This method checks various fields to determine if a work item is team-related.
        """
        try:
            team_related_items = []
            team_indicators = []
            
            for work_item in work_items:
                # Check if work item is team-related
                is_team_related = False
                indicator_reason = ""
                
                # Check area path for team name
                area_path = work_item.fields.get('System.AreaPath', '')
                if team.lower() in area_path.lower():
                    is_team_related = True
                    indicator_reason = f"Area path contains team name: {area_path}"
                
                # Check assigned to field for team members
                assigned_to = work_item.fields.get('System.AssignedTo', '')
                if assigned_to and team.lower() in str(assigned_to).lower():
                    is_team_related = True
                    indicator_reason = f"Assigned to contains team name: {assigned_to}"
                
                # Check tags for team indicators
                tags = work_item.fields.get('System.Tags', '')
                if tags and team.lower() in str(tags).lower():
                    is_team_related = True
                    indicator_reason = f"Tags contain team name: {tags}"
                
                # Check title for team indicators
                title = work_item.fields.get('System.Title', '')
                if title and team.lower() in title.lower():
                    is_team_related = True
                    indicator_reason = f"Title contains team name: {title[:50]}..."
                
                if is_team_related:
                    team_related_items.append(work_item)
                    team_indicators.append(indicator_reason)
            
            if team_related_items:
                logger.info(f"Found {len(team_related_items)} team-related work items")
                logger.info("Team indicators found:")
                for i, indicator in enumerate(team_indicators[:5]):  # Show first 5 indicators
                    logger.info(f"  {i+1}. {indicator}")
                if len(team_indicators) > 5:
                    logger.info(f"  ... and {len(team_indicators) - 5} more")
            
            return team_related_items
            
        except Exception as e:
            logger.error(f"Error filtering work items by team: {e}")
            return []
    
    def get_all_states_combined(self, project, team, work_item_type, limit):
        """
        Get work items from multiple common states to simulate "All" state.
        This avoids the VS402337 error by querying states individually.
        """
        try:
            logger.info(f"Getting work items from multiple states for team '{team}' to simulate 'All' state")
            
            # Get all available states first
            try:
                all_states = self.get_work_item_states(project)
                logger.info(f"Available states in project: {all_states}")
            except Exception as e:
                logger.warning(f"Could not get available states: {e}")
                all_states = ['Active', 'In Progress', 'New', 'Resolved', 'Closed']
            
            # Use a more intelligent approach - query recent work items with team filtering
            # instead of trying to query all states
            logger.info("Using intelligent team filtering approach instead of state-by-state queries")
            
            # Build a query that looks for team-related work items in recent time period
            from datetime import datetime, timedelta
            recent_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
            
            wiql_query = f"""
            SELECT [System.Id], [System.Title], [System.State], [System.WorkItemType], [System.AssignedTo], [System.CreatedDate]
            FROM workitems
            WHERE [System.TeamProject] = '{project}'
             AND [System.CreatedDate] >= '{recent_date}'
             AND [System.WorkItemType] IN ('User Story', 'Task', 'Bug', 'Feature', 'Epic', 'Test Case', 'Test Plan', 'Test Suite')
             AND [System.State] IN ('Active', 'In Progress', 'New', 'Resolved', 'Closed', 'Completed')
             ORDER BY [System.CreatedDate] DESC
            """
            
            logger.info(f"Executing intelligent team filtering query:")
            logger.info(wiql_query)
            
            wiql = {"query": wiql_query}
            query_result = self.work_item_client.query_by_wiql(wiql).work_items
            
            if not query_result:
                logger.info(f"No work items found in recent period for project '{project}'")
                return []
            
            # Limit results to prevent VS402337 error
            max_items = min(limit * 2, 200)  # Allow more items for team filtering
            if len(query_result) > max_items:
                logger.info(f"Limited results to {max_items} items to prevent VS402337 error")
                query_result = query_result[:max_items]
            
            logger.info(f"Found {len(query_result)} total work items, filtering by team indicators...")
            
            # Get all work items in batch for better performance
            all_work_items = self.get_work_items_batch([int(res.id) for res in query_result])
            
            # Filter by team (this is less reliable but provides a fallback)
            # Look for team-related indicators in the work items
            team_related_items = []
            team_indicators = []
            
            for work_item in all_work_items:
                # Check if work item is team-related
                is_team_related = False
                indicator_reason = ""
                
                # Check area path for team name (case insensitive)
                area_path = work_item.fields.get('System.AreaPath', '')
                if team.lower() in area_path.lower():
                    is_team_related = True
                    indicator_reason = f"Area path contains team name: {area_path}"
                
                # Check assigned to field for team members
                assigned_to = work_item.fields.get('System.AssignedTo', '')
                if assigned_to and team.lower() in str(assigned_to).lower():
                    is_team_related = True
                    indicator_reason = f"Assigned to contains team name: {assigned_to}"
                
                # Check tags for team indicators
                tags = work_item.fields.get('System.Tags', '')
                if tags and team.lower() in str(tags).lower():
                    is_team_related = True
                    indicator_reason = f"Tags contain team name: {tags}"
                
                # Check title for team indicators
                title = work_item.fields.get('System.Title', '')
                if title and team.lower() in title.lower():
                    is_team_related = True
                    indicator_reason = f"Title contains team name: {title[:50]}..."
                
                # Check iteration path for team indicators
                iteration_path = work_item.fields.get('System.IterationPath', '')
                if iteration_path and team.lower() in iteration_path.lower():
                    is_team_related = True
                    indicator_reason = f"Iteration path contains team name: {iteration_path}"
                
                if is_team_related:
                    team_related_items.append(work_item)
                    team_indicators.append(indicator_reason)
            
            logger.info(f"Found {len(team_related_items)} team-related work items")
            if team_indicators:
                logger.info("Team indicators found:")
                for i, indicator in enumerate(team_indicators[:10], 1):  # Show first 10
                    logger.info(f"   {i}. {indicator}")
                if len(team_indicators) > 10:
                    logger.info(f"   ... and {len(team_indicators) - 10} more")
            
            # Limit to requested limit
            if len(team_related_items) > limit:
                team_related_items = team_related_items[:limit]
                logger.info(f"Limited team-related items to {limit} as requested")
            
            logger.info(f"[SUCCESS] Retrieved {len(team_related_items)} team-related work items from all states")
            return team_related_items
            
        except Exception as e:
            logger.error(f"Error getting work items from all states: {e}")
            return []

    def get_work_item_types(self, project):
        """
        Get all available work item types for a project.
        
        Args:
            project (str): The name of the project.
            
        Returns:
            list: A list of work item type names.
        """
        try:
            logger.info(f"Getting work item types for project '{project}'")
            
            # Get the work item tracking client
            work_item_tracking_client = self.connection.clients.get_work_item_tracking_client()
            
            # Get work item types
            work_item_types = work_item_tracking_client.get_work_item_types(project)
            
            if not work_item_types:
                logger.warning(f"No work item types found for project '{project}'")
                return []
            
            # Extract the names
            type_names = [wit.name for wit in work_item_types if hasattr(wit, 'name')]
            
            logger.info(f"Found {len(type_names)} work item types: {type_names}")
            return type_names
            
        except Exception as e:
            logger.error(f"Error getting work item types: {e}")
            # Return default types as fallback
            default_types = ["User Story", "Bug", "Task", "Epic", "Feature", "Issue", "Test Case"]
            logger.info(f"Using default work item types: {default_types}")
            return default_types

    def get_work_item_states(self, project):
        """
        Get all available work item states for a project.
        
        Args:
            project (str): The name of the project.
            
        Returns:
            list: A list of state names.
        """
        try:
            logger.info(f"Getting work item states for project '{project}'")
            
            # Get the work item tracking client
            work_item_tracking_client = self.connection.clients.get_work_item_tracking_client()
            
            # Get work item types first
            work_item_types = work_item_tracking_client.get_work_item_types(project)
            
            if not work_item_types:
                logger.warning(f"No work item types found for project '{project}'")
                return []
            
            # Collect all unique states from all work item types
            all_states = set()
            for wit in work_item_types:
                if hasattr(wit, 'states'):
                    for state in wit.states:
                        if hasattr(state, 'name'):
                            all_states.add(state.name)
            
            # Convert to list and sort
            state_names = sorted(list(all_states))
            
            if not state_names:
                logger.warning(f"No states found for project '{project}'")
                # Return default states as fallback
                default_states = ["Active", "Closed", "Resolved", "New", "In Progress", "Removed"]
                logger.info(f"Using default states: {default_states}")
                return default_states
            
            logger.info(f"Found {len(state_names)} unique states: {state_names}")
            return state_names
            
        except Exception as e:
            logger.error(f"Error getting work item states: {e}")
            # Return default states as fallback
            default_states = ["Active", "Closed", "Resolved", "New", "In Progress", "Removed"]
            logger.info(f"Using default states: {default_states}")
            return default_states

    def get_work_item_states_for_type(self, project, work_item_type):
        """
        Get available work item states for a specific work item type.
        
        Args:
            project (str): The name of the project.
            work_item_type (str): The work item type to get states for.
            
        Returns:
            list: A list of state names for the specific work item type.
        """
        try:
            logger.info(f"Getting work item states for type '{work_item_type}' in project '{project}'")
            
            # Get the work item tracking client
            work_item_tracking_client = self.connection.clients.get_work_item_tracking_client()
            
            # Get work item types first
            work_item_types = work_item_tracking_client.get_work_item_types(project)
            
            if not work_item_types:
                logger.warning(f"No work item types found for project '{project}'")
                return []
            
            # Find the specific work item type
            target_wit = None
            for wit in work_item_types:
                if hasattr(wit, 'name') and wit.name == work_item_type:
                    target_wit = wit
                    break
            
            if not target_wit:
                logger.warning(f"Work item type '{work_item_type}' not found in project '{project}'")
                # Return default states as fallback
                default_states = ["Active", "Closed", "Resolved", "New", "In Progress", "Removed"]
                logger.info(f"Using default states: {default_states}")
                return default_states
            
            # Get states for this specific work item type
            states = []
            if hasattr(target_wit, 'states'):
                for state in target_wit.states:
                    if hasattr(state, 'name'):
                        states.append(state.name)
            
            # Sort the states
            state_names = sorted(states)
            
            if not state_names:
                logger.warning(f"No states found for work item type '{work_item_type}'")
                # Return default states as fallback
                default_states = ["Active", "Closed", "Resolved", "New", "In Progress", "Removed"]
                logger.info(f"Using default states: {default_states}")
                return default_states
            
            logger.info(f"Found {len(state_names)} states for '{work_item_type}': {state_names}")
            return state_names
            
        except Exception as e:
            logger.error(f"Error getting work item states for type '{work_item_type}': {e}")
            # Return default states as fallback
            default_states = ["Active", "Closed", "Resolved", "New", "In Progress", "Removed"]
            logger.info(f"Using default states: {default_states}")
            return default_states

    def get_work_item_type_states_mapping(self, project):
        """
        Get a mapping of work item types to their available states.
        
        Args:
            project (str): The name of the project.
            
        Returns:
            dict: A dictionary mapping work item type names to lists of state names.
        """
        try:
            logger.info(f"Getting work item type to states mapping for project '{project}'")
            
            # Get the work item tracking client
            work_item_tracking_client = self.connection.clients.get_work_item_tracking_client()
            
            # Get work item types first
            work_item_types = work_item_tracking_client.get_work_item_types(project)
            
            if not work_item_types:
                logger.warning(f"No work item types found for project '{project}'")
                return {}
            
            # Build the mapping
            type_states_mapping = {}
            for wit in work_item_types:
                if hasattr(wit, 'name'):
                    work_item_type_name = wit.name
                    states = []
                    
                    if hasattr(wit, 'states'):
                        for state in wit.states:
                            if hasattr(state, 'name'):
                                states.append(state.name)
                    
                    # Sort the states
                    type_states_mapping[work_item_type_name] = sorted(states)
                    logger.info(f"'{work_item_type_name}': {len(states)} states")
            
            logger.info(f"Created mapping for {len(type_states_mapping)} work item types")
            return type_states_mapping
            
        except Exception as e:
            logger.error(f"Error getting work item type to states mapping: {e}")
            # Return default mapping as fallback
            default_mapping = {
                "User Story": ["Active", "Closed", "Resolved", "New", "In Progress", "Removed"],
                "Bug": ["Active", "Closed", "Resolved", "New", "In Progress", "Removed"],
                "Task": ["Active", "Closed", "Resolved", "New", "In Progress", "Removed"],
                "Epic": ["Active", "Closed", "Resolved", "New", "In Progress", "Removed"],
                "Feature": ["Active", "Closed", "Resolved", "New", "In Progress", "Removed"]
            }
            logger.info(f"Using default mapping: {default_mapping}")
            return default_mapping

    def get_work_item_hierarchy(self, work_item_id):
        """
        Get the complete hierarchy for a work item (Team -> Epic -> Feature -> User Story -> Bug/Task).
        
        Args:
            work_item_id (int): The ID of the work item to get hierarchy for.
            
        Returns:
            dict: Dictionary containing hierarchy information with keys:
                - 'work_item': The work item itself
                - 'team': Team information
                - 'epic': Epic work item (if applicable)
                - 'feature': Feature work item (if applicable)
                - 'user_story': User Story work item (if applicable)
                - 'parent': Direct parent work item
                - 'children': List of direct child work items
                - 'hierarchy_path': List of work items from top to bottom
        """
        try:
            logger.info(f"Getting hierarchy for work item {work_item_id}")
            
            # Get the work item itself
            work_item = self.get_work_item(work_item_id)
            if not work_item:
                logger.error(f"Could not retrieve work item {work_item_id}")
                return None
            
            hierarchy = {
                'work_item': work_item,
                'team': None,
                'epic': None,
                'feature': None,
                'user_story': None,
                'parent': None,
                'children': [],
                'hierarchy_path': []
            }
            
            # Get team information from area path
            area_path = work_item.fields.get('System.AreaPath', '')
            if area_path:
                # Extract team name from area path (usually the last part before the project)
                path_parts = area_path.split('\\')
                if len(path_parts) >= 2:
                    team_name = path_parts[-2]  # Second to last part is usually the team
                    project_name = path_parts[-1]  # Last part is the project
                    
                    # Get team information with error handling
                    try:
                        teams = self.get_teams(project_name)
                        for team in teams:
                            if team.name == team_name:
                                hierarchy['team'] = team
                                break
                    except Exception as e:
                        logger.warning(f"Could not retrieve team information for project '{project_name}': {e}")
                        # Create a basic team object with available information
                        hierarchy['team'] = type('Team', (), {
                            'name': team_name,
                            'project_name': project_name,
                            'description': 'Team information not available due to permissions'
                        })()
            
            # Get parent and children relationships
            parent_id = work_item.fields.get('System.Parent')
            if parent_id:
                try:
                    hierarchy['parent'] = self.get_work_item(parent_id)
                except Exception as e:
                    logger.warning(f"Could not get parent work item {parent_id}: {e}")
                    hierarchy['parent'] = None
            
            # Get children work items
            try:
                children = self._get_work_item_children(work_item_id)
                hierarchy['children'] = children
            except Exception as e:
                logger.warning(f"Could not get children for work item {work_item_id}: {e}")
                hierarchy['children'] = []
            
            # Build hierarchy path by traversing up the parent chain
            hierarchy_path = []
            current_item = work_item
            max_depth = 10  # Prevent infinite loops
            depth = 0
            
            logger.info(f"Building hierarchy path for work item {work_item_id}")
            
            while current_item and depth < max_depth:
                hierarchy_path.append(current_item)
                parent_id = current_item.fields.get('System.Parent')
                logger.info(f"Level {depth}: Work item {current_item.id} ({current_item.fields.get('System.WorkItemType', 'Unknown')}) - Parent ID: {parent_id}")
                
                if parent_id:
                    try:
                        current_item = self.get_work_item(parent_id)
                        depth += 1
                        logger.info(f"Successfully retrieved parent work item {parent_id}")
                    except Exception as e:
                        logger.warning(f"Could not get parent work item {parent_id}: {e}")
                        break
                else:
                    logger.info(f"No parent found for work item {current_item.id}")
                    break
            
            # Reverse to get top-to-bottom order
            hierarchy['hierarchy_path'] = list(reversed(hierarchy_path))
            logger.info(f"Built hierarchy path with {len(hierarchy['hierarchy_path'])} levels")
            
            # Identify specific hierarchy levels
            for item in hierarchy['hierarchy_path']:
                work_item_type = item.fields.get('System.WorkItemType', '').lower()
                if work_item_type == 'epic':
                    hierarchy['epic'] = item
                elif work_item_type == 'feature':
                    hierarchy['feature'] = item
                elif work_item_type in ['user story', 'story']:
                    hierarchy['user_story'] = item
            
            logger.info(f"Retrieved hierarchy for work item {work_item_id}: {len(hierarchy['hierarchy_path'])} levels")
            return hierarchy
            
        except Exception as e:
            logger.error(f"Error getting hierarchy for work item {work_item_id}: {e}")
            return None

    def _get_work_item_children(self, work_item_id):
        """
        Get direct children of a work item.
        
        Args:
            work_item_id (int): The ID of the work item to get children for.
            
        Returns:
            list: List of child work items.
        """
        try:
            # Query for work items where this work item is the parent
            wiql_query = f"""
            SELECT [System.Id], [System.Title], [System.WorkItemType], [System.State], 
                   [System.AssignedTo], [System.CreatedDate], [System.AreaPath]
            FROM workitems
            WHERE [System.Parent] = {work_item_id}
            ORDER BY [System.Id]
            """
            
            work_item_tracking_client = self.connection.clients.get_work_item_tracking_client()
            query_result = work_item_tracking_client.query_by_wiql({'query': wiql_query})
            
            if not query_result.work_items:
                return []
            
            # Get the work items
            work_item_ids = [item.id for item in query_result.work_items]
            children = self.get_work_items_batch(work_item_ids)
            
            return children
            
        except Exception as e:
            logger.error(f"Error getting children for work item {work_item_id}: {e}")
            return []

    def get_work_item_hierarchy_display_text(self, hierarchy):
        """
        Generate a formatted text representation of the work item hierarchy.
        
        Args:
            hierarchy (dict): The hierarchy dictionary from get_work_item_hierarchy.
            
        Returns:
            str: Formatted text representation of the hierarchy.
        """
        if not hierarchy:
            return "No hierarchy information available."
        
        work_item = hierarchy['work_item']
        work_item_type = work_item.fields.get('System.WorkItemType', 'Unknown')
        work_item_title = work_item.fields.get('System.Title', 'No Title')
        work_item_state = work_item.fields.get('System.State', 'Unknown')
        
        # Start building the hierarchy text
        hierarchy_text = f"[INFO] Work Item Hierarchy for #{work_item.id}\n"
        hierarchy_text += f"Title: {work_item_title}\n"
        hierarchy_text += f"Type: {work_item_type} | State: {work_item_state}\n"
        hierarchy_text += "=" * 80 + "\n\n"
        
        # Add team information
        if hierarchy['team']:
            team_name = getattr(hierarchy['team'], 'name', 'Unknown Team')
            hierarchy_text += f"[TEAM] Team: {team_name}\n"
            if hasattr(hierarchy['team'], 'description') and hierarchy['team'].description:
                hierarchy_text += f"   Description: {hierarchy['team'].description}\n"
        else:
            hierarchy_text += "[TEAM] Team: Not specified\n"
        
        hierarchy_text += "\n"
        
        # Add hierarchy path (top to bottom)
        hierarchy_text += "[INFO] Hierarchy Path (Top to Bottom):\n"
        hierarchy_text += "-" * 40 + "\n"
        
        if hierarchy['hierarchy_path']:
            for i, item in enumerate(hierarchy['hierarchy_path']):
                item_type = item.fields.get('System.WorkItemType', 'Unknown')
                item_title = item.fields.get('System.Title', 'No Title')
                item_state = item.fields.get('System.State', 'Unknown')
                
                # Add indentation based on level
                indent = "  " * i
                
                # Add level indicator
                if i == 0:
                    # For the top-level item, check if it's an Epic, otherwise use ROOT
                    if item_type.lower() == 'epic':
                        level_indicator = "[EPIC] EPIC"
                    else:
                        level_indicator = "[ROOT] ROOT"
                elif item_type.lower() == 'epic':
                    level_indicator = "[EPIC] EPIC"
                elif item_type.lower() == 'feature':
                    level_indicator = "[FEATURE] FEATURE"
                elif item_type.lower() in ['user story', 'story']:
                    level_indicator = "[STORY] USER STORY"
                elif item_type.lower() == 'bug':
                    level_indicator = "[BUG] BUG"
                elif item_type.lower() == 'task':
                    level_indicator = "[TASK] TASK"
                else:
                    level_indicator = f"[{item_type.upper()}] {item_type.upper()}"
                
                hierarchy_text += f"{indent}{level_indicator}: #{item.id} - {item_title}\n"
                hierarchy_text += f"{indent}     State: {item_state}\n"
                
                # Add assigned to if available
                assigned_to = item.fields.get('System.AssignedTo', 'Unassigned')
                if assigned_to != 'Unassigned':
                    assigned_name = self.get_assigned_to_display_name(assigned_to)
                    hierarchy_text += f"{indent}     Assigned: {assigned_name}\n"
                
                hierarchy_text += "\n"
        else:
            hierarchy_text += "No hierarchy path available.\n\n"
        
        # Add children information
        if hierarchy['children']:
            hierarchy_text += f"👶 Direct Children ({len(hierarchy['children'])} items):\n"
            hierarchy_text += "-" * 40 + "\n"
            
            for child in hierarchy['children']:
                child_type = child.fields.get('System.WorkItemType', 'Unknown')
                child_title = child.fields.get('System.Title', 'No Title')
                child_state = child.fields.get('System.State', 'Unknown')
                
                hierarchy_text += f"  📝 {child_type}: #{child.id} - {child_title}\n"
                hierarchy_text += f"     State: {child_state}\n"
                
                # Add assigned to if available
                assigned_to = child.fields.get('System.AssignedTo', 'Unassigned')
                if assigned_to != 'Unassigned':
                    assigned_name = self.get_assigned_to_display_name(assigned_to)
                    hierarchy_text += f"     Assigned: {assigned_name}\n"
                
                hierarchy_text += "\n"
        else:
            hierarchy_text += "👶 Direct Children: None\n\n"
        
        return hierarchy_text

    def get_assigned_to_display_name(self, assigned_to_raw):
        """
        Extract display name from assigned to field.
        
        Args:
            assigned_to_raw: Raw assigned to field value.
            
        Returns:
            str: Display name for the assigned person.
        """
        if not assigned_to_raw or assigned_to_raw == 'Unassigned':
            return 'Unassigned'
        
        if isinstance(assigned_to_raw, dict):
            return assigned_to_raw.get('displayName', assigned_to_raw.get('uniqueName', 'Unknown'))
        elif isinstance(assigned_to_raw, str):
            return assigned_to_raw
        else:
            return str(assigned_to_raw)

    def query_related_work_items_by_title_keywords(self, project, work_item):
        """
        Query for work items related by keywords from title only (optimized single query approach).
        
        Args:
            project (str): The name of the project.
            work_item: The work item object to extract keywords from.
            
        Returns:
            list: A list of related work item objects based on title keyword matching.
        """
        try:
            print(f"[SEARCH] ADO Client: Starting optimized title keyword search for work item {work_item.id}")
            print(f"[INFO] ADO Client: Work item title: {work_item.fields.get('System.Title', 'No Title')}")
            
            # Extract keywords from title only
            title_keywords = self._extract_keywords_from_title_only(work_item)
            print(f"[KEYWORDS] ADO Client: Extracted title keywords: {title_keywords}")
            
            if not title_keywords:
                logger.info(f"No meaningful title keywords found for work item {work_item.id}")
                print(f"[ERROR] ADO Client: No title keywords extracted, returning empty list")
                return []
            
            # Build a single optimized WIQL query
            title_text = work_item.fields.get('System.Title', '')
            
            # Extract meaningful phrases from the title (remove common prefixes and numbers)
            import re
            
            # Remove common prefixes like "508:", "[PL CA]", "[Legal Updates]", etc.
            cleaned_title = re.sub(r'^\d+:\s*', '', title_text)  # Remove "508: " prefix
            cleaned_title = re.sub(r'^\[[^\]]+\]\s*', '', cleaned_title)  # Remove "[PL CA]" prefix
            cleaned_title = re.sub(r'^\[[^\]]+\]\s*', '', cleaned_title)  # Remove "[Legal Updates]" prefix
            cleaned_title = re.sub(r'^\[[^\]]+\]\s*', '', cleaned_title)  # Remove "[4.1.2]" prefix
            cleaned_title = re.sub(r'^:\s*', '', cleaned_title)  # Remove any remaining ": " prefix
            cleaned_title = cleaned_title.strip()
            
            print(f"[NOTE] ADO Client: Original title: {title_text}")
            print(f"[NOTE] ADO Client: Cleaned title: {cleaned_title}")
            
            # Helper function to escape single quotes for WIQL
            def escape_wiql_string(text):
                return text.replace("'", "''")
            
            # Create a single optimized search strategy
            search_conditions = []
            
            # Strategy 1: Use the most important keywords (top 3) for broad matching
            top_keywords = title_keywords[:3]  # Limit to top 3 keywords for performance
            for keyword in top_keywords:
                if len(keyword) > 3:  # Only use meaningful keywords
                    escaped_keyword = escape_wiql_string(keyword)
                    search_conditions.append(f"[System.Title] CONTAINS '{escaped_keyword}'")
            
            # Strategy 2: If we have a good cleaned title, also search for it
            if cleaned_title and len(cleaned_title) > 15:
                escaped_title = escape_wiql_string(cleaned_title)
                search_conditions.append(f"[System.Title] CONTAINS '{escaped_title}'")
            
            if not search_conditions:
                print(f"[ERROR] ADO Client: No valid search conditions created")
                return []
            
            # Combine conditions with OR
            where_clause = " OR ".join(search_conditions)
            
            # Add efficient filters for better performance
            work_item_type = work_item.fields.get('System.WorkItemType', '')
            
            # Build the single optimized query
            wiql_query = f"""
            SELECT [System.Id], [System.Title], [System.WorkItemType], [System.State], 
                   [System.AssignedTo], [System.CreatedBy], [System.CreatedDate], [System.Description]
            FROM WorkItems
            WHERE [System.TeamProject] = '{project}'
            AND [System.Id] != {work_item.id}
            AND ({where_clause})
            AND [System.State] <> 'Removed'
            AND [System.CreatedDate] >= @Today - 180
            {f"AND [System.WorkItemType] = '{work_item_type}'" if work_item_type else ""}
            ORDER BY [System.CreatedDate] DESC
            """
            
            # Print WIQL query to terminal for debugging
            print("\n" + "="*80)
            print(f"[QUERY] INTELLIGENT WIQL QUERY")
            print("="*80)
            print(wiql_query)
            print("="*80 + "\n")
            
            print(f"[INFO] ADO Client: Executing single optimized query with {len(search_conditions)} conditions")
            
            # Execute the single query
            work_item_client = self.connection.clients.get_work_item_tracking_client()
            wiql = {"query": wiql_query}
            
            try:
                query_result = work_item_client.query_by_wiql(wiql)
                print(f"[SUCCESS] ADO Client: Query executed successfully")
                
                if query_result and hasattr(query_result, 'work_items') and query_result.work_items:
                    print(f"[INFO] ADO Client: Found {len(query_result.work_items)} work items")
                    
                    # Process results with individual get_work_item calls
                    related_items = []
                    for item in query_result.work_items:
                        try:
                            full_item = work_item_client.get_work_item(item.id)
                            related_items.append(full_item)
                        except Exception as item_error:
                            print(f"[WARNING] ADO Client: Failed to get full details for work item {item.id}: {str(item_error)}")
                            # Continue with other items
                            continue
                    
                    logger.info(f"Found {len(related_items)} title-keyword-related work items for work item {work_item.id}")
                    print(f"[SUCCESS] ADO Client: Successfully retrieved {len(related_items)} related work items")
                    return related_items
                else:
                    print(f"[ERROR] ADO Client: No work items found in query result")
                    return []
                    
            except Exception as query_error:
                print(f"[ERROR] ADO Client: Query failed: {str(query_error)}")
                # Don't try multiple fallback queries - just return empty
                return []
                
        except Exception as e:
            logger.error(f"Error in title keyword search for work item {work_item.id}: {str(e)}")
            print(f"[ERROR] ADO Client: Title keyword search failed: {str(e)}")
            return []

    def _extract_keywords_from_title_only(self, work_item):
        """
        Extract meaningful keywords from work item title only (excluding description).
        
        Args:
            work_item: The work item object to extract keywords from.
            
        Returns:
            list: A list of meaningful keywords from title only.
        """
        import re
        
        print(f"[QUERY] ADO Client: Extracting title-only keywords from work item {work_item.id}")
        
        # Common stop words to filter out
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
            'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these',
            'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them',
            'my', 'your', 'his', 'her', 'its', 'our', 'their', 'mine', 'yours', 'hers', 'ours', 'theirs'
        }
        
        keywords = set()
        
        # Extract from title only
        if 'System.Title' in work_item.fields and work_item.fields['System.Title']:
            title_text = work_item.fields['System.Title']
            print(f"[NOTE] ADO Client: Title text: {title_text}")
            title_keywords = self._extract_keywords_from_text(title_text, stop_words)
            print(f"[KEYWORDS] ADO Client: Title keywords: {title_keywords}")
            keywords.update(title_keywords)
        else:
            print(f"[ERROR] ADO Client: No title found or title is empty")
        
        # Convert to list and sort by length (longer keywords first)
        keyword_list = list(keywords)
        keyword_list.sort(key=len, reverse=True)
        
        print(f"[KEYWORDS] ADO Client: Final title-only keywords: {keyword_list}")
        return keyword_list

    def _extract_keywords_from_text(self, text, stop_words):
        """
        Extract meaningful keywords from text.
        
        Args:
            text (str): The text to extract keywords from.
            stop_words (set): Set of stop words to filter out.
            
        Returns:
            list: A list of meaningful keywords.
        """
        import re
        
        if not text:
            return []
        
        # Convert to lowercase and extract words
        words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
        
        # Filter out stop words and short words
        keywords = []
        for word in words:
            if len(word) >= 3 and word not in stop_words:
                keywords.append(word)
        
        return keywords

    def query_work_items_by_team_and_user(self, project, team_name, user_name):
        """
        Query work items for a specific team and user.
        
        Args:
            project (str): The name of the project.
            team_name (str): The name of the team.
            user_name (str): The name of the user (display name).
            
        Returns:
            list: A list of work item objects.
        """
        try:
            logger.info(f"Querying work items for team '{team_name}' and user '{user_name}' in project '{project}'")
            
            # Get team area paths for filtering
            team_area_paths = self._get_team_area_paths(team_name, project)
            
            # Build WIQL query to find work items assigned to or created by the user in this team
            wiql_query = f"""
            SELECT [System.Id], [System.Title], [System.WorkItemType], [System.State], 
                   [System.AssignedTo], [System.CreatedBy], [System.ChangedBy], 
                   [System.CreatedDate], [System.ChangedDate], [System.AreaPath]
            FROM workitems
            WHERE [System.TeamProject] = '{project}'
             AND ([System.AssignedTo] CONTAINS '{user_name}' 
                  OR [System.CreatedBy] CONTAINS '{user_name}' 
                  OR [System.ChangedBy] CONTAINS '{user_name}')
             AND [System.WorkItemType] IN ('User Story', 'Task', 'Bug', 'Feature', 'Epic', 'Test Case', 'Test Plan', 'Test Suite')
             AND [System.State] IN ('Active', 'In Progress', 'New', 'Resolved', 'Closed', 'Completed')
            """
            
            # Add team area path filtering if available
            if team_area_paths:
                area_conditions = " OR ".join([f"[System.AreaPath] UNDER '{path}'" for path in team_area_paths])
                wiql_query += f" AND ({area_conditions})"
            
            wiql_query += " ORDER BY [System.ChangedDate] DESC"
            
            logger.info(f"Executing WIQL query for team '{team_name}' and user '{user_name}':")
            logger.info(wiql_query)
            
            wiql = {"query": wiql_query}
            query_result = self.work_item_client.query_by_wiql(wiql).work_items
            
            if not query_result:
                logger.info(f"No work items found for team '{team_name}' and user '{user_name}'")
                return []
            
            # Get detailed work item information
            work_item_ids = [item.id for item in query_result]
            work_items = self.work_item_client.get_work_items(work_item_ids)
            
            logger.info(f"Found {len(work_items)} work items for team '{team_name}' and user '{user_name}'")
            return work_items
            
        except Exception as e:
            logger.error(f"Error querying work items for team '{team_name}' and user '{user_name}': {e}")
            return []

def main():
    """Main function to demonstrate Azure DevOps access."""
    parser = argparse.ArgumentParser(description='Access Azure DevOps boards using Python.')
    
    # Required arguments
    parser.add_argument('--organization', required=True, help='Azure DevOps organization URL (e.g., https://dev.azure.com/your-organization)')
    parser.add_argument('--pat', required=True, help='Personal Access Token for authentication')
    parser.add_argument('--project', required=True, help='Project name')
    
    # Optional arguments
    parser.add_argument('--action', choices=['get-item', 'query-items', 'get-board', 'create-item', 'update-item'], 
                        default='query-items', help='Action to perform')
    parser.add_argument('--item-id', type=int, help='Work item ID (for get-item and update-item actions)')
    parser.add_argument('--item-type', default='User Story', help='Work item type (for query-items and create-item actions)')
    parser.add_argument('--state', help='Work item state (for query-items and update-item actions)')
    parser.add_argument('--title', help='Work item title (for create-item and update-item actions)')
    parser.add_argument('--description', help='Work item description (for create-item and update-item actions)')
    parser.add_argument('--assigned-to', help='Person to assign the work item to (for create-item and update-item actions)')
    parser.add_argument('--tags', help='Tags for the work item, semicolon-separated (for create-item and update-item actions)')
    parser.add_argument('--team', help='Team name (for get-board action)')
    parser.add_argument('--board', default='Stories', help='Board name (for get-board action)')
    parser.add_argument('--limit', type=int, default=50, help='Maximum number of work items to return (for query-items action)')
    
    args = parser.parse_args()
    
    try:
        # Create Azure DevOps client
        client = AzureDevOpsClient(args.organization, args.pat)
        
        # Perform the requested action
        if args.action == 'get-item':
            if not args.item_id:
                parser.error("--item-id is required for get-item action")
            
            work_item = client.get_work_item(args.item_id)
            client.print_work_item_details(work_item)
        
        elif args.action == 'query-items':
            work_items = client.query_work_items(
                project=args.project,
                work_item_type=args.item_type,
                state=args.state,
                limit=args.limit
            )
            client.print_work_items_summary(work_items)
        
        elif args.action == 'get-board':
            if not args.team:
                parser.error("--team is required for get-board action")
            
            columns = client.get_board_columns(args.project, args.team, args.board)
            client.print_board_columns(columns)
        
        elif args.action == 'create-item':
            if not args.title:
                parser.error("--title is required for create-item action")
            
            work_item = client.create_work_item(
                project=args.project,
                work_item_type=args.item_type,
                title=args.title,
                description=args.description,
                assigned_to=args.assigned_to,
                tags=args.tags
            )
            print(f"Created work item {work_item.id}: {args.title}")
            client.print_work_item_details(work_item)
        
        elif args.action == 'update-item':
            if not args.item_id:
                parser.error("--item-id is required for update-item action")
            
            work_item = client.update_work_item(
                work_item_id=args.item_id,
                title=args.title,
                description=args.description,
                state=args.state,
                assigned_to=args.assigned_to,
                tags=args.tags
            )
            print(f"Updated work item {args.item_id}")
            client.print_work_item_details(work_item)
    
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        print(f"Error: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
