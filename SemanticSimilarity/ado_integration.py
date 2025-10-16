"""
Azure DevOps Integration Module

This module provides integration between the semantic similarity engine
and the existing Azure DevOps AI Studio workflow.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import json
from datetime import datetime

from .semantic_similarity_engine import SyncSemanticSimilarityEngine, SemanticAnalysisResult
from .config import SemanticSimilarityConfig

logger = logging.getLogger(__name__)

@dataclass
class ADOIntegrationResult:
    """Result of Azure DevOps integration."""
    work_item_id: str
    semantic_analysis: SemanticAnalysisResult
    ado_work_items: List[Dict[str, Any]]
    integration_metadata: Dict[str, Any]
    success: bool
    error: Optional[str] = None

class ADOSemanticIntegration:
    """Integration layer between semantic similarity and Azure DevOps."""
    
    def __init__(self, config: SemanticSimilarityConfig, ado_client=None, openarena_client=None):
        self.config = config
        self.ado_client = ado_client
        self.openarena_client = openarena_client
        self.semantic_engine = SyncSemanticSimilarityEngine(config, openarena_client)
        
        logger.info("ADO Semantic Integration initialized")
    
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
    
    def analyze_work_item_semantic(self, work_item_id: int, 
                                 analysis_strategy: str = "ai_deep_dive") -> ADOIntegrationResult:
        """Analyze work item using semantic similarity (AI Deep Dive strategy)."""
        try:
            logger.info(f"Starting semantic analysis for work item {work_item_id} with strategy: {analysis_strategy}")
            
            # Step 1: Get work item from ADO
            if not self.ado_client:
                return ADOIntegrationResult(
                    work_item_id=str(work_item_id),
                    semantic_analysis=None,
                    ado_work_items=[],
                    integration_metadata={},
                    success=False,
                    error="ADO client not available"
                )
            
            work_item = self.ado_client.get_work_item(work_item_id)
            if not work_item:
                return ADOIntegrationResult(
                    work_item_id=str(work_item_id),
                    semantic_analysis=None,
                    ado_work_items=[],
                    integration_metadata={},
                    success=False,
                    error=f"Work item {work_item_id} not found"
                )
            
            # Step 2: Get work items based on strategy
            all_work_items = self._get_work_items_by_strategy(analysis_strategy, work_item)
            
            # Step 3: Build vector database with fetched work items
            logger.info(f"Building vector database with {len(all_work_items)} work items for semantic analysis")
            
            # Convert WorkItem objects to dictionaries
            all_work_items_dicts = [self._work_item_to_dict(wi) for wi in all_work_items]
            
            # Build vector database with all work items
            success = self.semantic_engine.build_vector_database(all_work_items_dicts)
            if not success:
                logger.warning("Failed to build vector database, proceeding with limited analysis")
                # Fallback to just the selected work item
                all_work_items_dicts = [self._work_item_to_dict(work_item)]
            
            # Step 4: Convert selected work item to dictionary for semantic analysis
            work_item_dict = self._work_item_to_dict(work_item)
            
            # Step 5: Perform semantic analysis
            semantic_analysis = self.semantic_engine.analyze_work_item(work_item_dict, all_work_items_dicts)
            
            # Step 5: Convert similarity results to ADO work items
            ado_work_items = self._convert_similarity_to_ado_work_items(semantic_analysis.similar_work_items)
            
            # Step 6: Create integration metadata
            integration_metadata = {
                "analysis_strategy": analysis_strategy,
                "total_work_items_analyzed": len(all_work_items),
                "similar_work_items_found": len(semantic_analysis.similar_work_items),
                "relationships_inferred": len(semantic_analysis.relationships),
                "clusters_identified": len(semantic_analysis.clusters),
                "processing_time": semantic_analysis.processing_time,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Semantic analysis completed: {len(ado_work_items)} similar work items found")
            
            return ADOIntegrationResult(
                work_item_id=str(work_item_id),
                semantic_analysis=semantic_analysis,
                ado_work_items=ado_work_items,
                integration_metadata=integration_metadata,
                success=True
            )
        
        except Exception as e:
            logger.error(f"Semantic analysis failed: {str(e)}")
            return ADOIntegrationResult(
                work_item_id=str(work_item_id),
                semantic_analysis=None,
                ado_work_items=[],
                integration_metadata={},
                success=False,
                error=str(e)
            )
    
    def _get_work_items_by_strategy(self, strategy: str, selected_work_item) -> List[Dict[str, Any]]:
        """Get work items based on analysis strategy."""
        if strategy == "ai_deep_dive":
            # For semantic similarity, we need to get work items from ADO to compare against
            logger.info("Using semantic similarity approach - fetching work items from ADO for comparison")
            
            # Get work items from the same area path and related areas
            area_path = selected_work_item.fields.get('System.AreaPath', '')
            work_items = []
            
            if area_path:
                try:
                    # Get work items from the same area path
                    area_work_items = self.ado_client.get_work_items_by_area_path(area_path, limit=200)
                    if area_work_items:
                        work_items.extend(area_work_items)
                        logger.info(f"Found {len(area_work_items)} work items in area: {area_path}")
                    
                    # Also get work items from parent area (broader scope)
                    parent_area = '/'.join(area_path.split('\\')[:-1]) if '\\' in area_path else area_path
                    if parent_area != area_path:
                        parent_work_items = self.ado_client.get_work_items_by_area_path(parent_area, limit=100)
                        if parent_work_items:
                            work_items.extend(parent_work_items)
                            logger.info(f"Found {len(parent_work_items)} work items in parent area: {parent_area}")
                    
                except Exception as e:
                    logger.warning(f"Failed to get work items by area path: {e}")
            
            # If no work items found, try getting recent work items
            if not work_items:
                try:
                    recent_work_items = self.ado_client.get_work_items(limit=100)
                    if recent_work_items:
                        work_items.extend(recent_work_items)
                        logger.info(f"Found {len(recent_work_items)} recent work items as fallback")
                except Exception as e:
                    logger.warning(f"Failed to get recent work items: {e}")
            
            # Always include the selected work item
            if selected_work_item not in work_items:
                work_items.insert(0, selected_work_item)
            
            logger.info(f"Total work items for semantic analysis: {len(work_items)}")
            return work_items
        
        elif strategy == "balanced_search":
            # Get work items from related teams/areas
            area_path = selected_work_item.fields.get('System.AreaPath', '')
            if area_path:
                # Extract team from area path
                team_path = '/'.join(area_path.split('\\')[:-1]) if '\\' in area_path else area_path
                work_items = self.ado_client.get_work_items_by_area_path(team_path, limit=1000)
                if selected_work_item not in work_items:
                    work_items.insert(0, selected_work_item)
                return work_items
            else:
                return [selected_work_item]
        
        elif strategy == "laser_focus":
            # Get work items from same team only
            area_path = selected_work_item.fields.get('System.AreaPath', '')
            if area_path:
                work_items = self.ado_client.get_work_items_by_area_path(area_path, limit=100)
                if selected_work_item not in work_items:
                    work_items.insert(0, selected_work_item)
                return work_items
            else:
                return [selected_work_item]
        
        else:
            # Default to just the selected work item for semantic analysis
            return [selected_work_item]
    
    def _is_database_populated(self) -> bool:
        """Check if vector database is populated."""
        stats = self.semantic_engine.get_database_stats()
        return stats['vector_database']['total_vectors'] > 0
    
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
                    # Semantic similarity specific fields
                    'semanticSimilarityScore': result.similarity_score,
                    'semanticRank': result.rank,
                    'semanticAnalysis': {
                        'similarity_score': result.similarity_score,
                        'rank': result.rank,
                        'embedding_model': metadata.get('embedding_info', {}).get('model', 'unknown'),
                        'processing_time': metadata.get('embedding_info', {}).get('processing_time', 0)
                    }
                }
                
                ado_work_items.append(ado_work_item)
            
            except Exception as e:
                logger.warning(f"Failed to convert similarity result to ADO format: {str(e)}")
                continue
        
        return ado_work_items
    
    def get_relationship_insights(self, analysis_result: ADOIntegrationResult) -> Dict[str, Any]:
        """Get relationship insights from semantic analysis."""
        if not analysis_result.semantic_analysis or not analysis_result.semantic_analysis.relationships:
            return {}
        
        relationships = analysis_result.semantic_analysis.relationships
        
        # Group by relationship type
        relationship_types = {}
        for rel in relationships:
            rel_type = rel.relationship_type
            if rel_type not in relationship_types:
                relationship_types[rel_type] = []
            relationship_types[rel_type].append(rel)
        
        # Calculate insights
        insights = {
            "total_relationships": len(relationships),
            "relationship_types": {},
            "high_confidence_relationships": [],
            "automatic_link_suggestions": [],
            "risk_indicators": [],
            "opportunity_indicators": []
        }
        
        for rel_type, rels in relationship_types.items():
            insights["relationship_types"][rel_type] = {
                "count": len(rels),
                "average_confidence": sum(r.confidence_score for r in rels) / len(rels),
                "high_confidence_count": sum(1 for r in rels if r.confidence_score >= 0.8)
            }
        
        # High confidence relationships
        insights["high_confidence_relationships"] = [
            {
                "work_item_1": rel.work_item_1_id,
                "work_item_2": rel.work_item_2_id,
                "relationship_type": rel.relationship_type,
                "confidence": rel.confidence_score,
                "explanation": rel.explanation
            }
            for rel in relationships if rel.confidence_score >= 0.8
        ]
        
        # Automatic link suggestions
        insights["automatic_link_suggestions"] = [
            {
                "work_item_1": rel.work_item_1_id,
                "work_item_2": rel.work_item_2_id,
                "relationship_type": rel.relationship_type,
                "confidence": rel.confidence_score,
                "suggested_action": rel.suggested_action
            }
            for rel in relationships if rel.is_automatic_linkable
        ]
        
        # Risk indicators
        risk_relationships = [r for r in relationships if r.relationship_type in ['blocking', 'dependency'] and r.impact_level == 'high']
        insights["risk_indicators"] = [
            {
                "work_item_1": rel.work_item_1_id,
                "work_item_2": rel.work_item_2_id,
                "risk_type": rel.relationship_type,
                "impact_level": rel.impact_level,
                "explanation": rel.explanation
            }
            for rel in risk_relationships
        ]
        
        # Opportunity indicators
        opportunity_relationships = [r for r in relationships if r.relationship_type in ['duplicate', 'refactoring'] and r.confidence_score >= 0.7]
        insights["opportunity_indicators"] = [
            {
                "work_item_1": rel.work_item_1_id,
                "work_item_2": rel.work_item_2_id,
                "opportunity_type": rel.relationship_type,
                "confidence": rel.confidence_score,
                "suggested_action": rel.suggested_action
            }
            for rel in opportunity_relationships
        ]
        
        return insights
    
    def export_analysis_report(self, analysis_result: ADOIntegrationResult, file_path: str) -> bool:
        """Export comprehensive analysis report."""
        try:
            report = {
                "work_item_id": analysis_result.work_item_id,
                "analysis_metadata": analysis_result.integration_metadata,
                "similar_work_items": analysis_result.ado_work_items,
                "relationship_insights": self.get_relationship_insights(analysis_result),
                "semantic_analysis": {
                    "clusters": [
                        {
                            "cluster_id": cluster.cluster_id,
                            "size": cluster.size,
                            "avg_similarity": cluster.avg_similarity,
                            "dominant_type": cluster.dominant_work_item_type,
                            "common_tags": cluster.common_tags
                        }
                        for cluster in analysis_result.semantic_analysis.clusters
                    ] if analysis_result.semantic_analysis else [],
                    "relationships": [
                        {
                            "work_item_1": rel.work_item_1_id,
                            "work_item_2": rel.work_item_2_id,
                            "relationship_type": rel.relationship_type,
                            "confidence": rel.confidence_score,
                            "explanation": rel.explanation,
                            "evidence": rel.evidence,
                            "suggested_action": rel.suggested_action,
                            "impact_level": rel.impact_level,
                            "is_automatic_linkable": rel.is_automatic_linkable
                        }
                        for rel in analysis_result.semantic_analysis.relationships
                    ] if analysis_result.semantic_analysis else []
                },
                "exported_at": datetime.now().isoformat()
            }
            
            with open(file_path, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            logger.info(f"Analysis report exported to {file_path}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to export analysis report: {str(e)}")
            return False

