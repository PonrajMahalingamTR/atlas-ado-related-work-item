"""
Enhanced ADO Integration Module

This module provides an enhanced integration between the semantic similarity engine
and Azure DevOps with automatic background ADO calls and system prompt-based embedding generation.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import json
import re
from datetime import datetime

from .semantic_similarity_engine import SyncSemanticSimilarityEngine, SemanticAnalysisResult
from .config import SemanticSimilarityConfig

logger = logging.getLogger(__name__)

@dataclass
class EnhancedADOIntegrationResult:
    """Result of enhanced Azure DevOps integration."""
    work_item_id: str
    semantic_analysis: SemanticAnalysisResult
    ado_work_items: List[Dict[str, Any]]
    integration_metadata: Dict[str, Any]
    success: bool
    error: Optional[str] = None

class EnhancedADOSemanticIntegration:
    """Enhanced integration layer between semantic similarity and Azure DevOps with background ADO calls."""
    
    def __init__(self, config: SemanticSimilarityConfig, ado_client=None, openarena_client=None):
        self.config = config
        self.ado_client = ado_client
        self.openarena_client = openarena_client
        self.semantic_engine = SyncSemanticSimilarityEngine(config, openarena_client)
        
        logger.info("Enhanced ADO Semantic Integration initialized")
    
    def _work_item_to_dict(self, work_item) -> Dict[str, Any]:
        """Convert WorkItem object to dictionary format expected by semantic engine."""
        if hasattr(work_item, 'fields'):
            # It's a WorkItem object
            assigned_to = work_item.fields.get('System.AssignedTo', 'Unassigned')
            # Extract displayName if assignedTo is an object
            if isinstance(assigned_to, dict) and 'displayName' in assigned_to:
                assigned_to = assigned_to['displayName']
            
            return {
                'id': work_item.id,
                'title': work_item.fields.get('System.Title', 'No Title'),
                'description': work_item.fields.get('System.Description', 'No Description'),
                'workItemType': work_item.fields.get('System.WorkItemType', 'Unknown'),
                'state': work_item.fields.get('System.State', 'Unknown'),
                'assignedTo': assigned_to,
                'areaPath': work_item.fields.get('System.AreaPath', 'Unknown'),
                'iterationPath': work_item.fields.get('System.IterationPath', 'Unknown'),
                'tags': work_item.fields.get('System.Tags', ''),
                'createdDate': work_item.fields.get('System.CreatedDate', ''),
                'changedDate': work_item.fields.get('System.ChangedDate', ''),
                'priority': work_item.fields.get('Microsoft.VSTS.Common.Priority', 0),
                'effort': work_item.fields.get('Microsoft.VSTS.Scheduling.Effort', 0),
                'fields': work_item.fields
            }
        else:
            # It's already a dictionary - also fix assignedTo if it's an object
            if isinstance(work_item, dict) and 'assignedTo' in work_item:
                assigned_to = work_item['assignedTo']
                if isinstance(assigned_to, dict) and 'displayName' in assigned_to:
                    work_item['assignedTo'] = assigned_to['displayName']
            return work_item
    
    def analyze_work_item_semantic_enhanced(self, work_item_id: int, 
                                          analysis_strategy: str = "ai_deep_dive") -> EnhancedADOIntegrationResult:
        """Enhanced semantic analysis with automatic background ADO calls and system prompt approach."""
        try:
            logger.info(f"Starting enhanced semantic analysis for work item {work_item_id} with strategy: {analysis_strategy}")
            
            # Step 1: Get selected work item from ADO
            if not self.ado_client:
                return EnhancedADOIntegrationResult(
                    work_item_id=str(work_item_id),
                    semantic_analysis=None,
                    ado_work_items=[],
                    integration_metadata={},
                    success=False,
                    error="ADO client not available"
                )
            
            selected_work_item = self.ado_client.get_work_item(work_item_id)
            if not selected_work_item:
                return EnhancedADOIntegrationResult(
                    work_item_id=str(work_item_id),
                    semantic_analysis=None,
                    ado_work_items=[],
                    integration_metadata={},
                    success=False,
                    error=f"Work item {work_item_id} not found"
                )
            
            # Step 2: Automatically invoke balanced search ADO call in background
            logger.info("Step 1: Invoking balanced search ADO call in background...")
            related_work_items = self._invoke_balanced_search_ado_call(selected_work_item)
            logger.info(f"Retrieved {len(related_work_items)} related work items from ADO")
            
            # Step 3: Store embeddings in vector database (LLM generates embeddings)
            logger.info("Step 2: Storing work items and generating embeddings in vector database...")
            embedding_success = self._store_work_items_in_vector_db(selected_work_item, related_work_items)
            
            if not embedding_success:
                logger.warning("Failed to store embeddings, falling back to basic similarity")
                # Fallback: return basic work items without semantic analysis
                ado_work_items = [self._work_item_to_dict(wi) for wi in related_work_items[:20]]
                semantic_analysis = SemanticAnalysisResult(
                    work_item_id=str(work_item_id),
                    similar_work_items=[],
                    clusters=[],
                    relationships=[],
                    analysis_metadata={'fallback': True, 'reason': 'embedding_storage_failed'},
                    processing_time=0,
                    success=True
                )
            else:
                # Step 4: Use vector similarity search to find similar work items
                logger.info("Step 3: Performing vector similarity search...")
                semantic_analysis = self._perform_vector_similarity_search(selected_work_item, related_work_items)
                
                # Step 5: Convert similarity results to ADO work items
                ado_work_items = self._convert_similarity_to_ado_work_items(semantic_analysis.similar_work_items)
            
            # Step 6: Create integration metadata
            integration_metadata = {
                "analysis_strategy": analysis_strategy,
                "enhanced_approach": True,
                "vector_similarity_approach": True,
                "selected_work_item_id": work_item_id,
                "related_work_items_fetched": len(related_work_items),
                "similar_work_items_found": len(semantic_analysis.similar_work_items),
                "relationships_inferred": len(semantic_analysis.relationships),
                "clusters_identified": len(semantic_analysis.clusters),
                "processing_time": semantic_analysis.processing_time,
                "embedding_storage_success": embedding_success,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Enhanced semantic analysis completed: {len(ado_work_items)} similar work items found")
            
            return EnhancedADOIntegrationResult(
                work_item_id=str(work_item_id),
                semantic_analysis=semantic_analysis,
                ado_work_items=ado_work_items,
                integration_metadata=integration_metadata,
                success=True
            )
        
        except Exception as e:
            logger.error(f"Enhanced semantic analysis failed: {str(e)}")
            return EnhancedADOIntegrationResult(
                work_item_id=str(work_item_id),
                semantic_analysis=None,
                ado_work_items=[],
                integration_metadata={},
                success=False,
                error=str(e)
            )
    
    def _invoke_balanced_search_ado_call(self, selected_work_item) -> List[Any]:
        """Invoke balanced search ADO call to get semantically related work items using 3-year batching logic across all teams."""
        try:
            # Extract meaningful phrases from the work item title
            phrases = self.ado_client._extract_meaningful_phrases(selected_work_item, phrase_length=2)
            
            if not phrases:
                logger.warning("No meaningful phrases found for balanced search, falling back to area path search")
                return self._fallback_to_area_path_search(selected_work_item)
            
            logger.info(f"BALANCED SEARCH - Using meaningful phrases: {phrases}")
            
            # Get project name from configuration
            project_name = self._get_project_name()
            if not project_name:
                logger.error("No project name found for balanced search")
                return self._fallback_to_area_path_search(selected_work_item)
            
            # Load all verified teams from mapping file (same as balanced search workflow)
            teams_to_search = self._load_all_verified_teams()
            if not teams_to_search:
                logger.warning("No verified teams found, falling back to area path search")
                return self._fallback_to_area_path_search(selected_work_item)
            
            logger.info(f"BALANCED SEARCH - Using all {len(teams_to_search)} verified teams for comprehensive search")
            
            # Use the balanced search method with 3-year batching to get semantically related work items across all teams
            related_work_item_refs = self.ado_client._execute_balanced_keyword_search_with_batching(
                project=project_name,
                work_item=selected_work_item,
                teams_to_search=teams_to_search,
                max_results_per_team=200,  # Increased limit for better coverage
                date_filter='last-6-months',  # This will be overridden by the batching logic
                work_item_types=['Bug', 'User Story', 'Task', 'Feature', 'Epic']
            )
            
            if not related_work_item_refs:
                logger.warning("No related work items found using balanced search, falling back to area path search")
                return self._fallback_to_area_path_search(selected_work_item)
            
            # Convert WorkItemReference objects to full work items
            work_item_ids = [ref.id for ref in related_work_item_refs]
            work_items = self.ado_client.get_work_items_batch(work_item_ids)
            
            # Always include the selected work item
            if selected_work_item not in work_items:
                work_items.insert(0, selected_work_item)
            
            logger.info(f"BALANCED SEARCH - Found {len(work_items)} semantically related work items using 3-year batching across all teams")
            return work_items
            
        except Exception as e:
            logger.error(f"Failed to invoke balanced search ADO call: {str(e)}")
            return self._fallback_to_area_path_search(selected_work_item)
    
    def _fallback_to_area_path_search(self, selected_work_item) -> List[Any]:
        """Fallback to area path search if balanced search fails."""
        try:
            area_path = selected_work_item.fields.get('System.AreaPath', '')
            work_items = []
            
            if area_path:
                # Get work items from the same area path only
                area_work_items = self.ado_client.get_work_items_by_area_path(area_path, limit=200)
                if area_work_items:
                    work_items.extend(area_work_items)
                    logger.info(f"FALLBACK - Found {len(area_work_items)} work items in area: {area_path}")
            
            # If no work items found, try getting recent work items
            if not work_items:
                recent_work_items = self.ado_client.get_work_items(limit=100)
                if recent_work_items:
                    work_items.extend(recent_work_items)
                    logger.info(f"FALLBACK - Found {len(recent_work_items)} recent work items")
            
            # Always include the selected work item
            if selected_work_item not in work_items:
                work_items.insert(0, selected_work_item)
            
            return work_items
            
        except Exception as e:
            logger.error(f"Failed to fallback to area path search: {str(e)}")
            return [selected_work_item]
    
    def _get_project_name(self) -> str:
        """Get project name from configuration."""
        try:
            import os
            config_file = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'ado_settings.txt')
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith('project=') and '=' in line:
                            return line.split('=', 1)[1]
            return os.getenv('AZURE_DEVOPS_PROJECT', 'Your Project Name')
        except Exception as e:
            logger.error(f"Failed to get project name: {str(e)}")
            return 'Your Project Name'
    
    def _load_all_verified_teams(self) -> List[str]:
        """Load all verified teams from mapping file (same as balanced search workflow)."""
        try:
            import os
            import json
            # Fix the path - go up one level from SemanticSimilarity to project root, then to config
            config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'team_area_paths.json')
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    team_mappings = json.load(f)
                    mappings = team_mappings.get('mappings', {})
                    # Get all verified teams
                    teams_to_search = [name for name, data in mappings.items() if data.get('verified', False)]
                    logger.info(f"Loaded {len(teams_to_search)} verified teams from mapping file")
                    return teams_to_search
            else:
                logger.error(f"Team mapping file not found at {config_path}")
                return []
        except Exception as e:
            logger.error(f"Failed to load verified teams: {str(e)}")
            return []
    
    def _store_work_items_in_vector_db(self, selected_work_item, related_work_items: List[Any]) -> bool:
        """Store work items and their embeddings in the vector database for future similarity searches."""
        try:
            # Convert work items to dictionaries
            all_work_items = [self._work_item_to_dict(selected_work_item)]
            all_work_items.extend([self._work_item_to_dict(wi) for wi in related_work_items])
            
            logger.info(f"Storing {len(all_work_items)} work items in vector database")
            
            # Clear the vector database to ensure only current work items are stored
            logger.info("Clearing vector database to store fresh embeddings for current work items")
            self.semantic_engine.vector_db.clear_database()
            
            # Build vector database with all work items (no duplicate checking needed)
            success = self.semantic_engine.build_vector_database(all_work_items)
            
            if success:
                logger.info(f"Successfully stored {len(all_work_items)} work items in vector database (fresh embeddings)")
            else:
                logger.warning("Failed to store work items in vector database")
                return False
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to store work items in vector database: {str(e)}")
            return False
    
    def _perform_vector_similarity_search(self, selected_work_item, related_work_items: List[Any]) -> SemanticAnalysisResult:
        """Perform vector similarity search to find similar work items using the stored embeddings."""
        try:
            logger.info("Performing vector similarity search for work item similarity")
            
            # Convert selected work item to dictionary
            selected_work_item_dict = self._work_item_to_dict(selected_work_item)
            
            # Use vector database to find similar work items (reuse existing embeddings)
            similar_work_items = self.semantic_engine.vector_db.find_similar_work_items(
                selected_work_item_dict, 
                top_k=40,  # Increased to capture all relevant items including history keyword items
                threshold=0.65  # Lowered threshold for better recall
            )
            
            if similar_work_items:
                logger.info(f"Vector similarity search found {len(similar_work_items)} similar work items")
                
                # Create semantic analysis result
                from .semantic_similarity_engine import SemanticAnalysisResult
                
                return SemanticAnalysisResult(
                    work_item_id=str(selected_work_item.id),
                    similar_work_items=similar_work_items,
                    clusters=[],  # Not used in this approach
                    relationships=[],  # Not used in this approach
                    analysis_metadata={
                        'approach': 'vector_similarity_search',
                        'total_work_items_analyzed': len(related_work_items),
                        'similar_work_items_found': len(similar_work_items)
                    },
                    processing_time=0.0,  # Will be calculated by caller
                    success=True
                )
            else:
                logger.warning("Vector similarity search found no similar work items")
                return SemanticAnalysisResult(
                    work_item_id=str(selected_work_item.id),
                    similar_work_items=[],
                    clusters=[],
                    relationships=[],
                    analysis_metadata={'approach': 'vector_similarity_search', 'no_similar_found': True},
                    processing_time=0.0,
                    success=True
                )
            
        except Exception as e:
            logger.error(f"Failed to perform vector similarity search: {str(e)}")
            # Return empty result on error
            return SemanticAnalysisResult(
                work_item_id=str(selected_work_item.id),
                similar_work_items=[],
                clusters=[],
                relationships=[],
                analysis_metadata={'error': str(e), 'approach': 'vector_similarity_failed'},
                processing_time=0,
                success=False,
                error=str(e)
            )
    
    
    
    
    def _convert_similarity_to_ado_work_items(self, similarity_results: List[Any]) -> List[Dict[str, Any]]:
        """Convert similarity results to ADO work item format."""
        ado_work_items = []
        
        for result in similarity_results:
            try:
                # Get work item metadata
                metadata = result.metadata
                work_item = metadata.get('work_item', {})
                
                if not work_item:
                    continue
                
                # Convert to ADO format
                assigned_to = work_item.get('assignedTo', 'Unassigned')
                # Extract displayName if assignedTo is an object
                if isinstance(assigned_to, dict) and 'displayName' in assigned_to:
                    assigned_to = assigned_to['displayName']
                
                ado_work_item = {
                    'id': work_item.get('id', result.work_item_id),
                    'title': work_item.get('title', 'No Title'),
                    'workItemType': work_item.get('workItemType', 'Unknown'),
                    'state': work_item.get('state', 'Unknown'),
                    'assignedTo': assigned_to,
                    'areaPath': work_item.get('areaPath', 'Unknown'),
                    'iterationPath': work_item.get('iterationPath', 'Unknown'),
                    'tags': work_item.get('tags', ''),
                    'description': work_item.get('description', ''),
                    'createdDate': work_item.get('createdDate', ''),
                    'changedDate': work_item.get('changedDate', ''),
                    'priority': work_item.get('priority', 0),
                    'effort': work_item.get('effort', 0),
                    'fields': work_item.get('fields', {}),
                    # Enhanced similarity specific fields
                    'semanticSimilarityScore': result.similarity_score,
                    'semanticRank': result.rank,
                    'semanticAnalysis': {
                        'similarity_score': result.similarity_score,
                        'rank': result.rank,
                        'explanation': metadata.get('explanation', ''),
                        'matching_factors': metadata.get('matching_factors', []),
                        'approach': 'enhanced_system_prompt'
                    }
                }
                
                ado_work_items.append(ado_work_item)
            
            except Exception as e:
                logger.warning(f"Failed to convert similarity result to ADO format: {str(e)}")
                continue
        
        return ado_work_items
    
    def get_relationship_insights(self, analysis_result: EnhancedADOIntegrationResult) -> Dict[str, Any]:
        """Get relationship insights from enhanced semantic analysis."""
        if not analysis_result.semantic_analysis or not analysis_result.semantic_analysis.similar_work_items:
            return {}
        
        similar_items = analysis_result.semantic_analysis.similar_work_items
        
        # Calculate insights
        insights = {
            "total_similar_items": len(similar_items),
            "average_similarity": sum(item.similarity_score for item in similar_items) / len(similar_items),
            "high_similarity_items": [
                {
                    "work_item_id": item.work_item_id,
                    "similarity_score": item.similarity_score,
                    "explanation": item.metadata.get('explanation', ''),
                    "matching_factors": item.metadata.get('matching_factors', [])
                }
                for item in similar_items if item.similarity_score >= 0.8
            ],
            "approach": "enhanced_system_prompt",
            "analysis_metadata": analysis_result.integration_metadata
        }
        
        return insights
