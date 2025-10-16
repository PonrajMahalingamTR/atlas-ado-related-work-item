"""
Relationship Inference Module

This module provides LLM-based relationship inference for work items.
It analyzes semantically similar work items and infers relationship types and strengths.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import json
import re

from .config import InferenceConfig
from .vector_db import SimilarityResult

logger = logging.getLogger(__name__)

@dataclass
class RelationshipType:
    """Types of relationships between work items."""
    DEPENDENCY = "dependency"
    DUPLICATE = "duplicate"
    RELATED_FEATURE = "related_feature"
    PARENT_CHILD = "parent_child"
    BLOCKING = "blocking"
    TECHNICAL_DEBT = "technical_debt"
    TESTING = "testing"
    INTEGRATION = "integration"
    REFACTORING = "refactoring"
    CROSS_TEAM = "cross_team"

@dataclass
class RelationshipInference:
    """Result of relationship inference between work items."""
    work_item_1_id: str
    work_item_2_id: str
    relationship_type: str
    confidence_score: float
    explanation: str
    evidence: List[str]
    suggested_action: str
    impact_level: str  # "high", "medium", "low"
    is_automatic_linkable: bool

class RelationshipInferenceEngine:
    """Engine for inferring relationships between work items using LLM analysis."""
    
    def __init__(self, config: InferenceConfig, openarena_client=None):
        self.config = config
        self.openarena_client = openarena_client
        self.relationship_types = [
            RelationshipType.DEPENDENCY,
            RelationshipType.DUPLICATE,
            RelationshipType.RELATED_FEATURE,
            RelationshipType.PARENT_CHILD,
            RelationshipType.BLOCKING,
            RelationshipType.TECHNICAL_DEBT,
            RelationshipType.TESTING,
            RelationshipType.INTEGRATION,
            RelationshipType.REFACTORING,
            RelationshipType.CROSS_TEAM
        ]
    
    def infer_relationships(self, similarity_results: List[SimilarityResult], 
                          work_item_metadata: Dict[str, Dict[str, Any]]) -> List[RelationshipInference]:
        """Infer relationships between work items based on similarity results."""
        if not similarity_results:
            return []
        
        # Group similar work items for batch processing
        relationship_groups = self._group_similar_work_items(similarity_results)
        
        all_inferences = []
        
        for group in relationship_groups:
            try:
                # Create inference prompt for this group
                prompt = self._create_inference_prompt(group, work_item_metadata)
                
                # Get LLM analysis
                if self.openarena_client:
                    llm_response = self._get_llm_analysis(prompt)
                else:
                    llm_response = self._get_mock_analysis(group)
                
                # Parse LLM response
                inferences = self._parse_llm_response(llm_response, group)
                all_inferences.extend(inferences)
                
            except Exception as e:
                logger.error(f"Failed to infer relationships for group: {str(e)}")
                continue
        
        # Filter and rank results
        filtered_inferences = self._filter_and_rank_inferences(all_inferences)
        
        logger.info(f"Inferred {len(filtered_inferences)} relationships from {len(similarity_results)} similarity results")
        return filtered_inferences
    
    def _group_similar_work_items(self, similarity_results: List[SimilarityResult]) -> List[List[SimilarityResult]]:
        """Group similar work items for batch processing."""
        # Group by similarity score ranges
        groups = []
        current_group = []
        
        for result in similarity_results:
            if not current_group or len(current_group) >= 5:  # Max 5 items per group
                if current_group:
                    groups.append(current_group)
                current_group = [result]
            else:
                current_group.append(result)
        
        if current_group:
            groups.append(current_group)
        
        return groups
    
    def _create_inference_prompt(self, similarity_group: List[SimilarityResult], 
                                work_item_metadata: Dict[str, Dict[str, Any]]) -> str:
        """Create LLM prompt for relationship inference."""
        work_items_info = []
        
        for result in similarity_group:
            metadata = work_item_metadata.get(result.work_item_id, {})
            work_item = metadata.get('work_item', {})
            
            # Extract work item details
            title = work_item.get('title', 'No Title')
            if 'fields' in work_item and 'System.Title' in work_item['fields']:
                title = work_item['fields']['System.Title']
            
            description = work_item.get('description', 'No Description')
            if 'fields' in work_item and 'System.Description' in work_item['fields']:
                description = work_item['fields']['System.Description']
            
            work_item_type = work_item.get('workItemType', 'Unknown')
            if 'fields' in work_item and 'System.WorkItemType' in work_item['fields']:
                work_item_type = work_item['fields']['System.WorkItemType']
            
            area_path = work_item.get('areaPath', 'Unknown')
            if 'fields' in work_item and 'System.AreaPath' in work_item['fields']:
                area_path = work_item['fields']['System.AreaPath']
            
            work_items_info.append({
                'id': result.work_item_id,
                'title': title,
                'description': description,
                'type': work_item_type,
                'area_path': area_path,
                'similarity_score': result.similarity_score
            })
        
        prompt = f"""You are an expert Azure DevOps work item analyst. Analyze the following work items that have been identified as semantically similar and determine the relationships between them.

WORK ITEMS TO ANALYZE:
{json.dumps(work_items_info, indent=2)}

RELATIONSHIP TYPES TO CONSIDER:
1. DEPENDENCY: One work item must be completed before another
2. DUPLICATE: Work items describe the same or very similar functionality
3. RELATED_FEATURE: Work items implement related features or components
4. PARENT_CHILD: One work item is a parent or child of another
5. BLOCKING: One work item blocks progress on another
6. TECHNICAL_DEBT: Work items related to code quality improvements
7. TESTING: Work items related to testing the same functionality
8. INTEGRATION: Work items that need to work together
9. REFACTORING: Work items related to code refactoring
10. CROSS_TEAM: Work items that span multiple teams

ANALYSIS REQUIREMENTS:
- Analyze each pair of work items in the group
- Determine the most likely relationship type
- Provide a confidence score (0.0 to 1.0)
- Explain the reasoning behind the relationship
- List specific evidence supporting the relationship
- Suggest appropriate actions
- Assess the impact level (high/medium/low)
- Determine if the relationship should be automatically linked

OUTPUT FORMAT (JSON):
{{
  "relationships": [
    {{
      "work_item_1_id": "string",
      "work_item_2_id": "string", 
      "relationship_type": "string",
      "confidence_score": 0.0-1.0,
      "explanation": "string",
      "evidence": ["string1", "string2"],
      "suggested_action": "string",
      "impact_level": "high|medium|low",
      "is_automatic_linkable": true/false
    }}
  ]
}}

Please analyze the work items and provide relationship inferences in the specified JSON format."""

        return prompt
    
    def _get_llm_analysis(self, prompt: str) -> str:
        """Get LLM analysis using OpenArena client."""
        try:
            if not self.openarena_client:
                raise ValueError("OpenArena client not available")
            
            # Always use Azure OpenAI workflow for semantic analysis
            workflow_id = self.openarena_client.workflow_ids.get('azure_openai', 'gemini2pro')
            
            # Log the request details (websocket client will handle detailed logging)
            logger.info(f"OpenArena Inference Request - Workflow ID: {workflow_id}, Model: azure_openai")
            
            response, cost_tracker = self.openarena_client.query_workflow(
                workflow_id=workflow_id,
                query=prompt,
                is_persistence_allowed=False
            )
            
            # Log the response details (websocket client will handle detailed logging)
            logger.info(f"OpenArena Inference Response - Length: {len(str(response))} characters")
            logger.info(f"OpenArena Inference Response - Cost: ${cost_tracker.get('total_cost', cost_tracker.get('cost', 0)):.6f}")
            
            logger.info(f"LLM analysis completed using {self.config.model_name}")
            return response
        
        except Exception as e:
            logger.error(f"LLM analysis failed: {str(e)}")
            raise
    
    def _get_mock_analysis(self, similarity_group: List[SimilarityResult]) -> str:
        """Get mock analysis for development/testing."""
        relationships = []
        
        for i in range(len(similarity_group)):
            for j in range(i + 1, len(similarity_group)):
                item1 = similarity_group[i]
                item2 = similarity_group[j]
                
                # Simple mock relationship based on similarity score
                if item1.similarity_score > 0.8:
                    relationship_type = "duplicate"
                    confidence = item1.similarity_score
                    suggested_action = "Review for potential merge"
                elif item1.similarity_score > 0.6:
                    relationship_type = "related_feature"
                    confidence = item1.similarity_score * 0.8
                    suggested_action = "Consider linking as related"
                else:
                    relationship_type = "related_feature"
                    confidence = item1.similarity_score * 0.6
                    suggested_action = "Monitor for potential relationship"
                
                relationship = {
                    "work_item_1_id": item1.work_item_id,
                    "work_item_2_id": item2.work_item_id,
                    "relationship_type": relationship_type,
                    "confidence_score": confidence,
                    "explanation": f"Semantic similarity score of {item1.similarity_score:.3f} suggests potential relationship",
                    "evidence": ["Semantic similarity", "Similar content patterns"],
                    "suggested_action": suggested_action,
                    "impact_level": "medium" if confidence > 0.7 else "low",
                    "is_automatic_linkable": confidence > self.config.confidence_threshold
                }
                relationships.append(relationship)
        
        return json.dumps({"relationships": relationships}, indent=2)
    
    def _parse_llm_response(self, llm_response: str, similarity_group: List[SimilarityResult]) -> List[RelationshipInference]:
        """Parse LLM response and create RelationshipInference objects."""
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
            if not json_match:
                logger.warning("No JSON found in LLM response")
                return []
            
            response_data = json.loads(json_match.group())
            relationships_data = response_data.get('relationships', [])
            
            inferences = []
            for rel_data in relationships_data:
                try:
                    inference = RelationshipInference(
                        work_item_1_id=rel_data['work_item_1_id'],
                        work_item_2_id=rel_data['work_item_2_id'],
                        relationship_type=rel_data['relationship_type'],
                        confidence_score=float(rel_data['confidence_score']),
                        explanation=rel_data['explanation'],
                        evidence=rel_data.get('evidence', []),
                        suggested_action=rel_data['suggested_action'],
                        impact_level=rel_data['impact_level'],
                        is_automatic_linkable=rel_data.get('is_automatic_linkable', False)
                    )
                    inferences.append(inference)
                
                except (KeyError, ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse relationship data: {str(e)}")
                    continue
            
            return inferences
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {str(e)}")
            return []
    
    def _filter_and_rank_inferences(self, inferences: List[RelationshipInference]) -> List[RelationshipInference]:
        """Filter and rank relationship inferences."""
        # Filter by confidence threshold
        filtered = [
            inf for inf in inferences 
            if inf.confidence_score >= self.config.confidence_threshold
        ]
        
        # Remove duplicates (same pair in different order)
        seen_pairs = set()
        unique_inferences = []
        
        for inf in filtered:
            pair = tuple(sorted([inf.work_item_1_id, inf.work_item_2_id]))
            if pair not in seen_pairs:
                seen_pairs.add(pair)
                unique_inferences.append(inf)
        
        # Sort by confidence score (descending)
        unique_inferences.sort(key=lambda x: x.confidence_score, reverse=True)
        
        # Limit results
        return unique_inferences[:self.config.max_relationships]
    
    def create_relationship_summary(self, inferences: List[RelationshipInference]) -> Dict[str, Any]:
        """Create summary of relationship inferences."""
        if not inferences:
            return {}
        
        # Count by relationship type
        type_counts = {}
        confidence_scores = []
        impact_levels = {"high": 0, "medium": 0, "low": 0}
        automatic_linkable = 0
        
        for inf in inferences:
            type_counts[inf.relationship_type] = type_counts.get(inf.relationship_type, 0) + 1
            confidence_scores.append(inf.confidence_score)
            impact_levels[inf.impact_level] += 1
            if inf.is_automatic_linkable:
                automatic_linkable += 1
        
        return {
            "total_relationships": len(inferences),
            "relationship_types": type_counts,
            "average_confidence": sum(confidence_scores) / len(confidence_scores),
            "confidence_distribution": {
                "high": sum(1 for s in confidence_scores if s >= 0.8),
                "medium": sum(1 for s in confidence_scores if 0.6 <= s < 0.8),
                "low": sum(1 for s in confidence_scores if s < 0.6)
            },
            "impact_levels": impact_levels,
            "automatic_linkable": automatic_linkable,
            "automatic_linkable_percentage": (automatic_linkable / len(inferences)) * 100
        }
    
    def suggest_automatic_links(self, inferences: List[RelationshipInference]) -> List[Dict[str, Any]]:
        """Suggest work items that should be automatically linked."""
        automatic_links = []
        
        for inf in inferences:
            if inf.is_automatic_linkable and inf.confidence_score >= self.config.confidence_threshold:
                link_suggestion = {
                    "work_item_1_id": inf.work_item_1_id,
                    "work_item_2_id": inf.work_item_2_id,
                    "relationship_type": inf.relationship_type,
                    "confidence_score": inf.confidence_score,
                    "reasoning": inf.explanation,
                    "suggested_action": inf.suggested_action
                }
                automatic_links.append(link_suggestion)
        
        return automatic_links



