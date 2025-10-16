"""
Enhanced Azure DevOps Work Item Filtering System

This module provides comprehensive filtering capabilities for Azure DevOps work items,
including multi-threaded API calls for filter prepopulation and client-side filtering.
"""

import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

logger = logging.getLogger(__name__)

class EnhancedFilterManager:
    """Manages enhanced filtering capabilities for Azure DevOps work items."""
    
    def __init__(self, ado_client):
        """Initialize the enhanced filter manager."""
        self.ado_client = ado_client
        self.filter_cache = {}
        self.cache_timestamp = {}
        self.cache_ttl = 300  # 5 minutes cache TTL
        
    def get_date_range_options(self) -> Dict[str, Tuple[datetime, datetime]]:
        """Get predefined date range options."""
        now = datetime.now()
        
        # Calculate current iteration (assuming 2-week sprints)
        current_week = now.isocalendar()[1]
        sprint_start_week = ((current_week - 1) // 2) * 2 + 1
        current_sprint_start = now - timedelta(days=now.weekday() + (current_week - sprint_start_week) * 7)
        current_sprint_end = current_sprint_start + timedelta(days=13)
        
        # Previous iteration
        previous_sprint_start = current_sprint_start - timedelta(days=14)
        previous_sprint_end = current_sprint_start - timedelta(days=1)
        
        # Current quarter
        current_quarter = (now.month - 1) // 3 + 1
        quarter_start_month = (current_quarter - 1) * 3 + 1
        current_quarter_start = datetime(now.year, quarter_start_month, 1)
        if current_quarter == 4:
            current_quarter_end = datetime(now.year + 1, 1, 1) - timedelta(days=1)
        else:
            next_quarter_start_month = current_quarter * 3 + 1
            current_quarter_end = datetime(now.year, next_quarter_start_month, 1) - timedelta(days=1)
        
        # Previous quarter
        if current_quarter == 1:
            previous_quarter_start = datetime(now.year - 1, 10, 1)
            previous_quarter_end = datetime(now.year - 1, 12, 31)
        else:
            prev_quarter_start_month = (current_quarter - 2) * 3 + 1
            previous_quarter_start = datetime(now.year, prev_quarter_start_month, 1)
            previous_quarter_end = current_quarter_start - timedelta(days=1)
        
        return {
            "Current Iteration": (current_sprint_start, current_sprint_end),
            "Previous Iteration": (previous_sprint_start, previous_sprint_end),
            "Current Quarter": (current_quarter_start, current_quarter_end),
            "Previous Quarter": (previous_quarter_start, previous_quarter_end),
            "Last 7 days": (now - timedelta(days=7), now),
            "Last 30 days": (now - timedelta(days=30), now),
            "Last 3 months": (now - timedelta(days=90), now),
            "Last 6 months": (now - timedelta(days=180), now),
            "Last year": (datetime(now.year - 1, 1, 1), datetime(now.year - 1, 12, 31)),
            "This quarter": (current_quarter_start, current_quarter_end),
            "Last quarter": (previous_quarter_start, previous_quarter_end),
            "This year": (datetime(now.year, 1, 1), now),
            "Last year": (datetime(now.year - 1, 1, 1), datetime(now.year - 1, 12, 31))
        }
    
    def prepopulate_filters_async(self, project: str, team: Optional[str] = None) -> Dict[str, Any]:
        """Prepopulate filter options using multi-threaded API calls."""
        logger.info(f"Starting async filter prepopulation for project '{project}' and team '{team}'")
        
        # Use ThreadPoolExecutor for concurrent API calls
        with ThreadPoolExecutor(max_workers=8) as executor:
            # Submit all filter population tasks
            future_to_filter = {
                executor.submit(self._get_work_item_types, project): 'work_item_types',
                executor.submit(self._get_work_item_states, project): 'work_item_states',
                executor.submit(self._get_sub_states, project): 'sub_states',
                executor.submit(self._get_assigned_users, project, team): 'assigned_users',
                executor.submit(self._get_iteration_paths, project, team): 'iteration_paths',
                executor.submit(self._get_area_paths, project, team): 'area_paths',
                executor.submit(self._get_tags, project, team): 'tags',
                executor.submit(self._get_priorities, project): 'priorities',
                executor.submit(self._get_created_by_users, project, team): 'created_by_users',
                executor.submit(self._get_changed_by_users, project, team): 'changed_by_users',
                executor.submit(self._get_saved_queries, project): 'saved_queries'
            }
            
            # Collect results
            filter_data = {}
            for future in as_completed(future_to_filter):
                filter_name = future_to_filter[future]
                try:
                    result = future.result()
                    filter_data[filter_name] = result
                    if isinstance(result, list):
                        logger.info(f"[SUCCESS] Successfully populated {filter_name}: {len(result)} items")
                        if len(result) > 0:
                            logger.info(f"   Sample values: {result[:3]}{'...' if len(result) > 3 else ''}")
                    else:
                        logger.info(f"[SUCCESS] Successfully populated {filter_name}: {result}")
                except Exception as e:
                    logger.error(f"[ERROR] Error populating {filter_name}: {e}")
                    filter_data[filter_name] = []
            
            # Add date range options
            filter_data['date_ranges'] = list(self.get_date_range_options().keys())
            
            # Cache the results
            cache_key = f"{project}_{team or 'all'}"
            self.filter_cache[cache_key] = filter_data
            self.cache_timestamp[cache_key] = time.time()
            
            logger.info(f"Completed async filter prepopulation for project '{project}' and team '{team}'")
            return filter_data
    
    def _get_work_item_types(self, project: str) -> List[str]:
        """Get available work item types."""
        try:
            return self.ado_client.get_work_item_types(project)
        except Exception as e:
            logger.error(f"Error getting work item types: {e}")
            return ["User Story", "Bug", "Task", "Epic", "Feature", "Issue", "Test Case"]
    
    def _get_work_item_states(self, project: str) -> List[str]:
        """Get available work item states."""
        try:
            return self.ado_client.get_work_item_states(project)
        except Exception as e:
            logger.error(f"Error getting work item states: {e}")
            return ["Active", "Closed", "Resolved", "New", "In Progress", "Removed"]
    
    def _get_sub_states(self, project: str) -> List[str]:
        """Get available sub-states by querying the work item type definitions."""
        try:
            logger.info(f"Getting sub-states from work item type definitions for project '{project}'")
            
            # Get work item types first
            work_item_types = self.ado_client.get_work_item_types(project)
            all_states = set()
            
            # For each work item type, get its state definitions
            for work_item_type in work_item_types[:5]:  # Limit to first 5 types to avoid too many API calls
                try:
                    # Get work item type definition
                    wit_definition = self.ado_client.work_item_client.get_work_item_type(project, work_item_type)
                    
                    # Extract states from the definition
                    if hasattr(wit_definition, 'states') and wit_definition.states:
                        for state in wit_definition.states:
                            if hasattr(state, 'name'):
                                all_states.add(state.name)
                            elif hasattr(state, 'value'):
                                all_states.add(state.value)
                    
                except Exception as e:
                    logger.warning(f"Error getting states for work item type '{work_item_type}': {e}")
                    continue
            
            # If we didn't get states from definitions, fall back to querying work items
            if not all_states:
                logger.info("No states found from definitions, querying work items...")
                wiql_query = f"""
                SELECT TOP 1000 [System.Id], [System.State]
                FROM workitems
                WHERE [System.TeamProject] = '{project}'
                ORDER BY [System.CreatedDate] DESC
                """
                
                wiql = {"query": wiql_query}
                query_result = self.ado_client.work_item_client.query_by_wiql(wiql)
                
                if query_result and hasattr(query_result, 'work_items') and query_result.work_items:
                    # Get work item IDs and fetch the actual work items
                    work_item_ids = [item.id for item in query_result.work_items[:100]]
                    if work_item_ids:
                        work_items = self.ado_client.get_work_items_batch(work_item_ids)
                        for work_item in work_items:
                            if hasattr(work_item, 'fields') and 'System.State' in work_item.fields:
                                state = work_item.fields['System.State']
                                if state:
                                    all_states.add(state)
            
            # Convert to sorted list
            sub_states = sorted(list(all_states))
            
            # If still no states found, add common states as fallback
            if not sub_states:
                common_sub_states = ['Active', 'Closed', 'New', 'In Progress', 'Resolved', 'Blocked']
                sub_states = common_sub_states
            
            logger.info(f"Found {len(sub_states)} unique sub-states: {sub_states}")
            return sub_states
            
        except Exception as e:
            logger.error(f"Error getting sub-states: {e}")
            return ['Active', 'Closed', 'New', 'In Progress', 'Resolved', 'Blocked']
    
    def _get_assigned_users(self, project: str, team: Optional[str] = None) -> List[str]:
        """Get list of users who have work items assigned to them."""
        try:
            # Get a sample of work items to extract unique assigned users
            logger.info(f"Getting assigned users from existing work items for project '{project}'")
            
            # Query a reasonable number of work items to get unique assigned users
            wiql_query = f"""
            SELECT [System.Id], [System.AssignedTo]
            FROM workitems
            WHERE [System.TeamProject] = '{project}'
            AND [System.AssignedTo] <> ''
            ORDER BY [System.CreatedDate] DESC
            """
            
            if team:
                wiql_query = f"""
                SELECT [System.Id], [System.AssignedTo]
                FROM workitems
                WHERE [System.TeamProject] = '{project}'
                AND [System.AreaPath] UNDER '{project}\\{team}'
                AND [System.AssignedTo] <> ''
                ORDER BY [System.CreatedDate] DESC
                """
            
            wiql = {"query": wiql_query}
            query_result = self.ado_client.work_item_client.query_by_wiql(wiql)
            
            users = set()
            if query_result and hasattr(query_result, 'work_items') and query_result.work_items:
                # Get work item IDs
                work_item_ids = [item.id for item in query_result.work_items[:100]]  # Limit to 100 items
                
                if work_item_ids:
                    # Get the actual work items with their fields
                    work_items = self.ado_client.get_work_items_batch(work_item_ids)
                    
                    for work_item in work_items:
                        if hasattr(work_item, 'fields') and 'System.AssignedTo' in work_item.fields:
                            assigned_to = work_item.fields['System.AssignedTo']
                            if assigned_to:
                                # Handle both string and dict formats
                                if isinstance(assigned_to, dict):
                                    display_name = assigned_to.get('displayName', assigned_to.get('uniqueName', str(assigned_to)))
                                else:
                                    display_name = str(assigned_to)
                                users.add(display_name)
            
            logger.info(f"Found {len(users)} unique assigned users")
            return sorted(list(users))
        except Exception as e:
            logger.error(f"Error getting assigned users: {e}")
            return []
    
    def _get_iteration_paths(self, project: str, team: Optional[str] = None) -> List[str]:
        """Get available iteration paths (sprints)."""
        try:
            logger.info(f"Getting iteration paths from existing work items for project '{project}'")
            
            # Query a reasonable number of work items to get unique iteration paths
            wiql_query = f"""
            SELECT [System.Id], [System.IterationPath]
            FROM workitems
            WHERE [System.TeamProject] = '{project}'
            AND [System.IterationPath] <> ''
            ORDER BY [System.CreatedDate] DESC
            """
            
            if team:
                wiql_query = f"""
                SELECT [System.Id], [System.IterationPath]
                FROM workitems
                WHERE [System.TeamProject] = '{project}'
                AND [System.AreaPath] UNDER '{project}\\{team}'
                AND [System.IterationPath] <> ''
                ORDER BY [System.CreatedDate] DESC
                """
            
            wiql = {"query": wiql_query}
            query_result = self.ado_client.work_item_client.query_by_wiql(wiql)
            
            iterations = set()
            if query_result and hasattr(query_result, 'work_items') and query_result.work_items:
                # Get work item IDs
                work_item_ids = [item.id for item in query_result.work_items[:100]]  # Limit to 100 items
                
                if work_item_ids:
                    # Get the actual work items with their fields
                    work_items = self.ado_client.get_work_items_batch(work_item_ids)
                    
                    for work_item in work_items:
                        if hasattr(work_item, 'fields') and 'System.IterationPath' in work_item.fields:
                            iteration = work_item.fields['System.IterationPath']
                            if iteration:
                                iterations.add(iteration)
            
            logger.info(f"Found {len(iterations)} unique iteration paths")
            return sorted(list(iterations))
        except Exception as e:
            logger.error(f"Error getting iteration paths: {e}")
            return []
    
    def _get_area_paths(self, project: str, team: Optional[str] = None) -> List[str]:
        """Get available area paths."""
        try:
            logger.info(f"Getting area paths from existing work items for project '{project}'")
            
            # Query a reasonable number of work items to get unique area paths
            wiql_query = f"""
            SELECT [System.Id], [System.AreaPath]
            FROM workitems
            WHERE [System.TeamProject] = '{project}'
            AND [System.AreaPath] <> ''
            ORDER BY [System.CreatedDate] DESC
            """
            
            if team:
                wiql_query = f"""
                SELECT [System.Id], [System.AreaPath]
                FROM workitems
                WHERE [System.TeamProject] = '{project}'
                AND [System.AreaPath] UNDER '{project}\\{team}'
                AND [System.AreaPath] <> ''
                ORDER BY [System.CreatedDate] DESC
                """
            
            wiql = {"query": wiql_query}
            query_result = self.ado_client.work_item_client.query_by_wiql(wiql)
            
            area_paths = set()
            if query_result and hasattr(query_result, 'work_items') and query_result.work_items:
                # Get work item IDs
                work_item_ids = [item.id for item in query_result.work_items[:100]]  # Limit to 100 items
                
                if work_item_ids:
                    # Get the actual work items with their fields
                    work_items = self.ado_client.get_work_items_batch(work_item_ids)
                    
                    for work_item in work_items:
                        if hasattr(work_item, 'fields') and 'System.AreaPath' in work_item.fields:
                            area_path = work_item.fields['System.AreaPath']
                            if area_path:
                                area_paths.add(area_path)
            
            logger.info(f"Found {len(area_paths)} unique area paths")
            return sorted(list(area_paths))
        except Exception as e:
            logger.error(f"Error getting area paths: {e}")
            return []
    
    def _get_tags(self, project: str, team: Optional[str] = None) -> List[str]:
        """Get all unique tags used in work items."""
        try:
            logger.info(f"Getting tags from existing work items for project '{project}'")
            
            # Query a reasonable number of work items to get unique tags
            wiql_query = f"""
            SELECT [System.Id], [System.Tags]
            FROM workitems
            WHERE [System.TeamProject] = '{project}'
            AND [System.Tags] <> ''
            ORDER BY [System.CreatedDate] DESC
            """
            
            if team:
                wiql_query = f"""
                SELECT [System.Id], [System.Tags]
                FROM workitems
                WHERE [System.TeamProject] = '{project}'
                AND [System.AreaPath] UNDER '{project}\\{team}'
                AND [System.Tags] <> ''
                ORDER BY [System.CreatedDate] DESC
                """
            
            wiql = {"query": wiql_query}
            query_result = self.ado_client.work_item_client.query_by_wiql(wiql)
            
            all_tags = set()
            if query_result and hasattr(query_result, 'work_items') and query_result.work_items:
                # Get work item IDs
                work_item_ids = [item.id for item in query_result.work_items[:100]]  # Limit to 100 items
                
                if work_item_ids:
                    # Get the actual work items with their fields
                    work_items = self.ado_client.get_work_items_batch(work_item_ids)
                    
                    for work_item in work_items:
                        if hasattr(work_item, 'fields') and 'System.Tags' in work_item.fields:
                            tags_str = work_item.fields['System.Tags']
                            if tags_str:
                                # Split tags by semicolon and clean them
                                tags = [tag.strip() for tag in tags_str.split(';') if tag.strip()]
                                all_tags.update(tags)
            
            logger.info(f"Found {len(all_tags)} unique tags")
            return sorted(list(all_tags))
        except Exception as e:
            logger.error(f"Error getting tags: {e}")
            return []
    
    def _get_priorities(self, project: str) -> List[str]:
        """Get available priority/severity levels."""
        try:
            # Query for priority field values (limit to recent items to avoid size limit)
            wiql_query = f"""
            SELECT TOP 1000 [System.Id], [Microsoft.VSTS.Common.Priority]
            FROM workitems
            WHERE [System.TeamProject] = '{project}'
            AND [Microsoft.VSTS.Common.Priority] <> ''
            ORDER BY [System.CreatedDate] DESC
            """
            
            wiql = {"query": wiql_query}
            query_result = self.ado_client.work_item_client.query_by_wiql(wiql)
            
            priorities = []
            if query_result and hasattr(query_result, 'work_items') and query_result.work_items:
                # Get work item IDs and fetch the actual work items
                work_item_ids = [item.id for item in query_result.work_items[:200]]  # Limit to 200 items
                if work_item_ids:
                    work_items = self.ado_client.get_work_items_batch(work_item_ids)
                    for work_item in work_items:
                        if hasattr(work_item, 'fields') and 'Microsoft.VSTS.Common.Priority' in work_item.fields:
                            priority = work_item.fields['Microsoft.VSTS.Common.Priority']
                            if priority and str(priority) not in priorities:
                                priorities.append(str(priority))
            
            # Add common priority levels if not found
            common_priorities = ['1 - Critical', '2 - High', '3 - Medium', '4 - Low', '5 - Very Low']
            for priority in common_priorities:
                if priority not in priorities:
                    priorities.append(priority)
            
            return sorted(priorities)
        except Exception as e:
            logger.error(f"Error getting priorities: {e}")
            return ['1 - Critical', '2 - High', '3 - Medium', '4 - Low', '5 - Very Low']
    
    def _get_created_by_users(self, project: str, team: Optional[str] = None) -> List[str]:
        """Get list of users who have created work items."""
        try:
            logger.info(f"Getting created by users from existing work items for project '{project}'")
            
            # Query a reasonable number of work items to get unique created by users
            wiql_query = f"""
            SELECT [System.Id], [System.CreatedBy]
            FROM workitems
            WHERE [System.TeamProject] = '{project}'
            AND [System.CreatedBy] <> ''
            ORDER BY [System.CreatedDate] DESC
            """
            
            if team:
                wiql_query = f"""
                SELECT [System.Id], [System.CreatedBy]
                FROM workitems
                WHERE [System.TeamProject] = '{project}'
                AND [System.AreaPath] UNDER '{project}\\{team}'
                AND [System.CreatedBy] <> ''
                ORDER BY [System.CreatedDate] DESC
                """
            
            wiql = {"query": wiql_query}
            query_result = self.ado_client.work_item_client.query_by_wiql(wiql)
            
            users = set()
            if query_result and hasattr(query_result, 'work_items') and query_result.work_items:
                # Get work item IDs
                work_item_ids = [item.id for item in query_result.work_items[:100]]  # Limit to 100 items
                
                if work_item_ids:
                    # Get the actual work items with their fields
                    work_items = self.ado_client.get_work_items_batch(work_item_ids)
                    
                    for work_item in work_items:
                        if hasattr(work_item, 'fields') and 'System.CreatedBy' in work_item.fields:
                            created_by = work_item.fields['System.CreatedBy']
                            if created_by:
                                # Handle both string and dict formats
                                if isinstance(created_by, dict):
                                    display_name = created_by.get('displayName', created_by.get('uniqueName', str(created_by)))
                                else:
                                    display_name = str(created_by)
                                users.add(display_name)
            
            logger.info(f"Found {len(users)} unique created by users")
            return sorted(list(users))
        except Exception as e:
            logger.error(f"Error getting created by users: {e}")
            return []
    
    def _get_changed_by_users(self, project: str, team: Optional[str] = None) -> List[str]:
        """Get list of users who have changed work items."""
        try:
            logger.info(f"Getting changed by users from existing work items for project '{project}'")
            
            # Query a reasonable number of work items to get unique changed by users
            wiql_query = f"""
            SELECT [System.Id], [System.ChangedBy]
            FROM workitems
            WHERE [System.TeamProject] = '{project}'
            AND [System.ChangedBy] <> ''
            ORDER BY [System.ChangedDate] DESC
            """
            
            if team:
                wiql_query = f"""
                SELECT [System.Id], [System.ChangedBy]
                FROM workitems
                WHERE [System.TeamProject] = '{project}'
                AND [System.AreaPath] UNDER '{project}\\{team}'
                AND [System.ChangedBy] <> ''
                ORDER BY [System.ChangedDate] DESC
                """
            
            wiql = {"query": wiql_query}
            query_result = self.ado_client.work_item_client.query_by_wiql(wiql)
            
            users = set()
            if query_result and hasattr(query_result, 'work_items') and query_result.work_items:
                # Get work item IDs
                work_item_ids = [item.id for item in query_result.work_items[:100]]  # Limit to 100 items
                
                if work_item_ids:
                    # Get the actual work items with their fields
                    work_items = self.ado_client.get_work_items_batch(work_item_ids)
                    
                    for work_item in work_items:
                        if hasattr(work_item, 'fields') and 'System.ChangedBy' in work_item.fields:
                            changed_by = work_item.fields['System.ChangedBy']
                            if changed_by:
                                # Handle both string and dict formats
                                if isinstance(changed_by, dict):
                                    display_name = changed_by.get('displayName', changed_by.get('uniqueName', str(changed_by)))
                                else:
                                    display_name = str(changed_by)
                                users.add(display_name)
            
            logger.info(f"Found {len(users)} unique changed by users")
            return sorted(list(users))
        except Exception as e:
            logger.error(f"Error getting changed by users: {e}")
            return []
    
    def _get_saved_queries(self, project: str) -> List[Dict[str, str]]:
        """Get saved/shared queries for the project."""
        try:
            # This would require additional API calls to get saved queries
            # For now, return some common query templates
            return [
                {"name": "Assigned to me", "query": "[System.AssignedTo] = @Me"},
                {"name": "Recently updated", "query": "[System.ChangedDate] >= @Today-7"},
                {"name": "High priority bugs", "query": "[System.WorkItemType] = 'Bug' AND [Microsoft.VSTS.Common.Priority] <= 2"},
                {"name": "Blocked items", "query": "[System.State] = 'Blocked'"},
                {"name": "Code review needed", "query": "[System.State] = 'Code Review'"}
            ]
        except Exception as e:
            logger.error(f"Error getting saved queries: {e}")
            return []
    
    def get_cached_filters(self, project: str, team: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get cached filter data if still valid."""
        cache_key = f"{project}_{team or 'all'}"
        
        if cache_key in self.filter_cache:
            if time.time() - self.cache_timestamp[cache_key] < self.cache_ttl:
                logger.info(f"Returning cached filter data for {cache_key}")
                return self.filter_cache[cache_key]
            else:
                logger.info(f"Cache expired for {cache_key}, will refresh")
                del self.filter_cache[cache_key]
                del self.cache_timestamp[cache_key]
        
        return None
    
    def apply_filters_to_work_items(self, work_items: List[Any], filters: Dict[str, Any]) -> List[Any]:
        """Apply client-side filters to work items."""
        if not filters:
            return work_items
        
        if not work_items:
            logger.info("No work items to filter")
            return []
        
        logger.info(f"Applying enhanced filters to {len(work_items)} work items")
        logger.info(f"Filter values: {filters}")
        
        filtered_items = work_items.copy()
        
        # Apply each filter
        for filter_name, filter_value in filters.items():
            if not filter_value or filter_value == "All":
                logger.info(f"Skipping filter '{filter_name}': value is '{filter_value}'")
                continue
            
            initial_count = len(filtered_items)
            logger.info(f"Applying filter '{filter_name}' = '{filter_value}' to {initial_count} items")
            
            if filter_name == "work_item_type":
                filtered_items = [item for item in filtered_items 
                                if item.fields.get('System.WorkItemType') == filter_value]
                logger.info(f"Work item type filter: {initial_count} -> {len(filtered_items)} items")
            
            elif filter_name == "state":
                filtered_items = [item for item in filtered_items 
                                if item.fields.get('System.State') == filter_value]
                logger.info(f"State filter: {initial_count} -> {len(filtered_items)} items")
            
            elif filter_name == "sub_state":
                # Sub-state filter should work independently of state filter
                # If both state and sub_state are specified, sub-state takes precedence
                if "state" in filters and filters["state"] != "All":
                    logger.info(f"Sub-state filter overriding state filter: '{filters['state']}' -> '{filter_value}'")
                    # Reset to original work items and apply only sub_state filter
                    filtered_items = [item for item in work_items 
                                    if item.fields.get('System.State') == filter_value]
                else:
                    filtered_items = [item for item in filtered_items 
                                    if item.fields.get('System.State') == filter_value]
                logger.info(f"Sub-state filter: {initial_count} -> {len(filtered_items)} items")
                # Debug: show some sample states
                if initial_count > 0:
                    sample_states = [item.fields.get('System.State', 'Unknown') for item in work_items[:5]]
                    logger.info(f"Sample states in work items: {sample_states}")
                    # Also show what we're looking for
                    logger.info(f"Looking for items with state: '{filter_value}'")
            
            elif filter_name == "assigned_to":
                filtered_items = [item for item in filtered_items 
                                if self._matches_assigned_to(item, filter_value)]
                logger.info(f"Assigned to filter: {initial_count} -> {len(filtered_items)} items")
            
            elif filter_name == "iteration_path":
                filtered_items = [item for item in filtered_items 
                                if item.fields.get('System.IterationPath') == filter_value]
                logger.info(f"Iteration path filter: {initial_count} -> {len(filtered_items)} items")
            
            elif filter_name == "area_path":
                filtered_items = [item for item in filtered_items 
                                if self._matches_area_path(item, filter_value)]
                logger.info(f"Area path filter: {initial_count} -> {len(filtered_items)} items")
            
            elif filter_name == "tags":
                filtered_items = [item for item in filtered_items 
                                if self._matches_tags(item, filter_value)]
                logger.info(f"Tags filter: {initial_count} -> {len(filtered_items)} items")
            
            elif filter_name == "priority":
                filtered_items = [item for item in filtered_items 
                                if self._matches_priority(item, filter_value)]
                logger.info(f"Priority filter: {initial_count} -> {len(filtered_items)} items")
            
            elif filter_name == "created_by":
                filtered_items = [item for item in filtered_items 
                                if self._matches_created_by(item, filter_value)]
                logger.info(f"Created by filter: {initial_count} -> {len(filtered_items)} items")
            
            elif filter_name == "changed_by":
                filtered_items = [item for item in filtered_items 
                                if self._matches_changed_by(item, filter_value)]
                logger.info(f"Changed by filter: {initial_count} -> {len(filtered_items)} items")
            
            elif filter_name == "date_range":
                # Apply date range filter based on the selected range
                date_ranges = self.get_date_range_options()
                logger.info(f"Available date ranges: {list(date_ranges.keys())}")
                if filter_value in date_ranges:
                    start_date, end_date = date_ranges[filter_value]
                    logger.info(f"Date range filter: {filter_value} -> {start_date} to {end_date}")
                    filtered_items = [item for item in filtered_items 
                                    if self._is_date_in_range(item, start_date, end_date)]
                    logger.info(f"Date range filter: {initial_count} -> {len(filtered_items)} items")
                else:
                    logger.warning(f"Date range '{filter_value}' not found in available ranges: {list(date_ranges.keys())}")
        
        logger.info(f"Final result: {len(work_items)} -> {len(filtered_items)} items after applying all filters")
        return filtered_items
    
    def _is_date_in_range(self, work_item: Any, start_date: datetime, end_date: datetime) -> bool:
        """Check if work item's relevant date is within the specified range."""
        # Check different date fields based on the filter type
        date_fields = ['System.CreatedDate', 'System.ChangedDate', 'Microsoft.VSTS.Common.ClosedDate']
        
        for field in date_fields:
            if field in work_item.fields:
                try:
                    item_date_str = work_item.fields[field]
                    if item_date_str:
                        # Parse the date string
                        if isinstance(item_date_str, str):
                            item_date = datetime.fromisoformat(item_date_str.replace('Z', '+00:00'))
                        else:
                            item_date = item_date_str
                        
                        # Handle timezone-aware vs timezone-naive comparison
                        # Convert timezone-aware dates to naive for comparison
                        if item_date.tzinfo is not None:
                            # Convert to UTC and remove timezone info for comparison
                            item_date_naive = item_date.utctimetuple()
                            item_date = datetime(*item_date_naive[:6])
                        
                        # Ensure start_date and end_date are also naive
                        if start_date.tzinfo is not None:
                            start_date = start_date.replace(tzinfo=None)
                        if end_date.tzinfo is not None:
                            end_date = end_date.replace(tzinfo=None)
                        
                        # Check if date is within range
                        if start_date <= item_date <= end_date:
                            return True
                except Exception as e:
                    logger.warning(f"Error parsing date {field}: {e}")
                    continue
        
        return False
    
    def _matches_assigned_to(self, work_item: Any, filter_value: str) -> bool:
        """Check if work item matches assigned to filter."""
        assigned_to = work_item.fields.get('System.AssignedTo', '')
        if isinstance(assigned_to, str):
            return filter_value.lower() in assigned_to.lower()
        else:
            return str(assigned_to) == filter_value
    
    def _matches_area_path(self, work_item: Any, filter_value: str) -> bool:
        """Check if work item matches area path filter."""
        area_path = work_item.fields.get('System.AreaPath', '')
        return filter_value.lower() in area_path.lower()
    
    def _matches_tags(self, work_item: Any, filter_value: str) -> bool:
        """Check if work item matches tags filter."""
        tags = work_item.fields.get('System.Tags', '')
        if filter_value.startswith('!'):  # Exclude filter
            exclude_tag = filter_value[1:]
            return exclude_tag.lower() not in tags.lower()
        else:  # Include filter
            return filter_value.lower() in tags.lower()
    
    def _matches_priority(self, work_item: Any, filter_value: str) -> bool:
        """Check if work item matches priority filter."""
        priority = work_item.fields.get('Microsoft.VSTS.Common.Priority', '')
        return str(priority) == filter_value
    
    def _matches_created_by(self, work_item: Any, filter_value: str) -> bool:
        """Check if work item matches created by filter."""
        created_by = work_item.fields.get('System.CreatedBy', '')
        if isinstance(created_by, str):
            return filter_value.lower() in created_by.lower()
        else:
            return str(created_by) == filter_value
    
    def _matches_changed_by(self, work_item: Any, filter_value: str) -> bool:
        """Check if work item matches changed by filter."""
        changed_by = work_item.fields.get('System.ChangedBy', '')
        if isinstance(changed_by, str):
            return filter_value.lower() in changed_by.lower()
        else:
            return str(changed_by) == filter_value
    
    def get_priority_options(self) -> List[str]:
        """Get available priority options."""
        return ["1 - Critical", "2 - High", "3 - Medium", "4 - Low"]
    
    def get_severity_options(self) -> List[str]:
        """Get available severity options for bugs."""
        return ["1 - Critical", "2 - High", "3 - Medium", "4 - Low"]
    
    def get_resolution_reason_options(self) -> List[str]:
        """Get available resolution reason options."""
        return [
            "Fixed",
            "Duplicate",
            "Won't Fix",
            "Cannot Reproduce",
            "Deferred",
            "As Designed",
            "Obsolete"
        ]
    
    def get_effort_options(self) -> List[str]:
        """Get available effort/story points options."""
        return ["1", "2", "3", "5", "8", "13", "21", "34", "55", "89"]
    
    def extract_filter_values_from_work_items(self, work_items: List[Any]) -> Dict[str, List[str]]:
        """Extract all possible filter values from a list of work items."""
        filter_values = {
            'work_item_types': set(),
            'work_item_states': set(),
            'assigned_users': set(),
            'priorities': set(),
            'tags': set(),
            'area_paths': set(),
            'iteration_paths': set(),
            'created_by_users': set(),
            'severities': set(),
            'resolutions': set(),
            'efforts': set()
        }
        
        for item in work_items:
            try:
                # Work item types
                if 'System.WorkItemType' in item.fields:
                    filter_values['work_item_types'].add(item.fields['System.WorkItemType'])
                
                # States
                if 'System.State' in item.fields:
                    filter_values['work_item_states'].add(item.fields['System.State'])
                
                # Assigned to
                if 'System.AssignedTo' in item.fields and item.fields['System.AssignedTo']:
                    assigned_to = self._get_display_name(item.fields['System.AssignedTo'])
                    filter_values['assigned_users'].add(assigned_to)
                
                # Priority
                if 'Microsoft.VSTS.Common.Priority' in item.fields:
                    priority = str(item.fields['Microsoft.VSTS.Common.Priority'])
                    filter_values['priorities'].add(priority)
                
                # Tags
                if 'System.Tags' in item.fields and item.fields['System.Tags']:
                    tag_list = item.fields['System.Tags'].split(';')
                    for tag in tag_list:
                        if tag.strip():
                            filter_values['tags'].add(tag.strip())
                
                # Area Path
                if 'System.AreaPath' in item.fields:
                    filter_values['area_paths'].add(item.fields['System.AreaPath'])
                
                # Iteration Path
                if 'System.IterationPath' in item.fields:
                    filter_values['iteration_paths'].add(item.fields['System.IterationPath'])
                
                # Created By
                if 'System.CreatedBy' in item.fields and item.fields['System.CreatedBy']:
                    created_by = self._get_display_name(item.fields['System.CreatedBy'])
                    filter_values['created_by_users'].add(created_by)
                
                # Severity (for bugs)
                if 'Microsoft.VSTS.Common.Severity' in item.fields:
                    filter_values['severities'].add(item.fields['Microsoft.VSTS.Common.Severity'])
                
                # Resolution Reason
                if 'Microsoft.VSTS.Common.ResolvedReason' in item.fields:
                    filter_values['resolutions'].add(item.fields['Microsoft.VSTS.Common.ResolvedReason'])
                
                # Effort/Story Points
                if 'Microsoft.VSTS.Scheduling.StoryPoints' in item.fields:
                    effort = str(item.fields['Microsoft.VSTS.Scheduling.StoryPoints'])
                    filter_values['efforts'].add(effort)
                    
            except Exception as e:
                logger.warning(f"Error extracting filter values from work item {item.id}: {e}")
                continue
        
        # Convert sets to sorted lists
        for key in filter_values:
            filter_values[key] = sorted(list(filter_values[key]))
        
        return filter_values
    
    def _get_display_name(self, identity_ref) -> str:
        """Extract display name from Azure DevOps identity reference."""
        try:
            if hasattr(identity_ref, 'display_name'):
                return identity_ref.display_name
            elif hasattr(identity_ref, 'unique_name'):
                return identity_ref.unique_name
            elif isinstance(identity_ref, str):
                return identity_ref
            else:
                return str(identity_ref)
        except Exception:
            return str(identity_ref)