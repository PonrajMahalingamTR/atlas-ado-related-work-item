"""
Semantic Similarity Engine

Main orchestrator for the semantic similarity analysis pipeline.
Coordinates all components to provide end-to-end semantic similarity analysis.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import asyncio
from datetime import datetime
import json

from .config import SemanticSimilarityConfig
from .openarena_embeddings import OpenArenaEmbeddings, EmbeddingResult
from .preprocessing import TextPreprocessor, PreprocessingResult
from .vector_db import VectorDatabase, SimilarityResult
from .similarity import SimilarityEngine, ClusterResult, SimilarityAnalysis
from .inference import RelationshipInferenceEngine, RelationshipInference

logger = logging.getLogger(__name__)

@dataclass
class SemanticAnalysisResult:
    """Complete result of semantic similarity analysis."""
    work_item_id: str
    similar_work_items: List[SimilarityResult]
    clusters: List[ClusterResult]
    relationships: List[RelationshipInference]
    analysis_metadata: Dict[str, Any]
    processing_time: float
    success: bool
    error: Optional[str] = None

class SemanticSimilarityEngine:
    """Main engine for semantic similarity analysis of work items."""
    
    def __init__(self, config: SemanticSimilarityConfig, openarena_client=None):
        self.config = config
        self.openarena_client = openarena_client
        
        # Initialize components
        self.preprocessor = TextPreprocessor(config.preprocessing)
        self.embeddings_client = OpenArenaEmbeddings(openarena_client)
        self.vector_db = VectorDatabase(config.vector_db)
        self.similarity_engine = SimilarityEngine(config.similarity)
        self.inference_engine = RelationshipInferenceEngine(config.inference, openarena_client)
        
        logger.info("Semantic Similarity Engine initialized")
    
    async def analyze_work_item(self, work_item: Dict[str, Any], 
                              all_work_items: List[Dict[str, Any]] = None) -> SemanticAnalysisResult:
        """Analyze a single work item for semantic similarities."""
        start_time = datetime.now()
        
        try:
            logger.info(f"Starting semantic analysis for work item {work_item.get('id', 'unknown')}")
            
            # Step 1: Preprocess work item
            preprocessing_result = self.preprocessor.preprocess_work_item(work_item)
            if not preprocessing_result.success:
                return SemanticAnalysisResult(
                    work_item_id=str(work_item.get('id', 'unknown')),
                    similar_work_items=[],
                    clusters=[],
                    relationships=[],
                    analysis_metadata={},
                    processing_time=0,
                    success=False,
                    error=f"Preprocessing failed: {preprocessing_result.error}"
                )
            
            # Step 2: Generate embedding for the work item
            embedding_result = await self.embeddings_client.generate_single_embedding(
                preprocessing_result.processed_text
            )
            if not embedding_result.success:
                return SemanticAnalysisResult(
                    work_item_id=str(work_item.get('id', 'unknown')),
                    similar_work_items=[],
                    clusters=[],
                    relationships=[],
                    analysis_metadata={},
                    processing_time=0,
                    success=False,
                    error=f"Embedding generation failed: {embedding_result.error}"
                )
            
            # Step 3: Search for similar work items with enhanced relevance scoring
            similar_work_items = self.vector_db.search_similar(
                embedding_result.embedding,
                top_k=self.config.vector_db.max_results,
                work_item_metadata=work_item
            )
            
            # Step 4: Perform clustering analysis if we have enough work items
            clusters = []
            if all_work_items and len(all_work_items) > 5:
                clusters = await self._perform_clustering_analysis(all_work_items)
            
            # Step 5: Infer relationships (disabled for performance)
            relationships = []
            # Temporarily disabled to avoid timeouts
            # if similar_work_items:
            #     relationships = self.inference_engine.infer_relationships(
            #         similar_work_items,
            #         self.vector_db.work_item_metadata
            #     )
            
            # Step 6: Create analysis metadata
            analysis_metadata = {
                "preprocessing": {
                    "original_length": preprocessing_result.text_length_before,
                    "processed_length": preprocessing_result.text_length_after,
                    "steps_applied": preprocessing_result.preprocessing_steps
                },
                "embedding": {
                    "model": embedding_result.model,
                    "usage_tokens": embedding_result.usage_tokens,
                    "processing_time": embedding_result.processing_time
                },
                "similarity": {
                    "total_similar_items": len(similar_work_items),
                    "similarity_threshold": self.config.vector_db.similarity_threshold
                },
                "clustering": {
                    "total_clusters": len(clusters),
                    "clustering_method": self.config.similarity.clustering_method
                },
                "relationships": {
                    "total_relationships": len(relationships),
                    "high_confidence": sum(1 for r in relationships if r.confidence_score >= 0.8),
                    "automatic_linkable": sum(1 for r in relationships if r.is_automatic_linkable)
                }
            }
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"Semantic analysis completed in {processing_time:.2f}s")
            
            return SemanticAnalysisResult(
                work_item_id=str(work_item.get('id', 'unknown')),
                similar_work_items=similar_work_items,
                clusters=clusters,
                relationships=relationships,
                analysis_metadata=analysis_metadata,
                processing_time=processing_time,
                success=True
            )
        
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Semantic analysis failed: {str(e)}")
            
            return SemanticAnalysisResult(
                work_item_id=str(work_item.get('id', 'unknown')),
                similar_work_items=[],
                clusters=[],
                relationships=[],
                analysis_metadata={},
                processing_time=processing_time,
                success=False,
                error=str(e)
            )
    
    async def build_vector_database(self, work_items: List[Dict[str, Any]]) -> bool:
        """Build vector database from work items."""
        try:
            logger.info(f"Building vector database from {len(work_items)} work items")
            
            # Step 1: Preprocess all work items
            preprocessing_results = self.preprocessor.preprocess_work_items(work_items)
            successful_preprocessing = [
                (work_items[i], result) for i, result in enumerate(preprocessing_results) 
                if result.success
            ]
            
            if not successful_preprocessing:
                logger.error("No work items successfully preprocessed")
                return False
            
            # Step 2: Generate embeddings
            texts = [result.processed_text for _, result in successful_preprocessing]
            embedding_results = await self.embeddings_client.generate_embeddings(texts)
            
            # Step 3: Add to vector database
            successful_work_items = []
            successful_embeddings = []
            
            for (work_item, _), embedding_result in zip(successful_preprocessing, embedding_results):
                if embedding_result.success:
                    successful_work_items.append(work_item)
                    successful_embeddings.append(embedding_result)
            
            if not successful_work_items:
                logger.error("No work items successfully embedded")
                return False
            
            # Step 4: Add to vector database
            success = self.vector_db.add_work_items(successful_work_items, successful_embeddings)
            
            if success:
                logger.info(f"Vector database built with {len(successful_work_items)} work items")
            else:
                logger.error("Failed to add work items to vector database")
            
            return success
        
        except Exception as e:
            logger.error(f"Failed to build vector database: {str(e)}")
            return False
    
    async def _perform_clustering_analysis(self, work_items: List[Dict[str, Any]]) -> List[ClusterResult]:
        """Perform clustering analysis on work items."""
        try:
            # Get embeddings for all work items
            work_item_ids = [str(wi.get('id', f'item_{i}')) for i, wi in enumerate(work_items)]
            
            # Check if we have embeddings in the database
            embeddings = []
            valid_work_items = []
            
            for work_item in work_items:
                work_item_id = str(work_item.get('id', 'unknown'))
                metadata = self.vector_db.get_work_item_metadata(work_item_id)
                
                if metadata and 'embedding' in metadata:
                    embeddings.append(metadata['embedding'])
                    valid_work_items.append(work_item)
                else:
                    # Generate embedding for this work item
                    preprocessing_result = self.preprocessor.preprocess_work_item(work_item)
                    if preprocessing_result.success:
                        embedding_result = await self.embeddings_client.generate_single_embedding(
                            preprocessing_result.processed_text
                        )
                        if embedding_result.success:
                            embeddings.append(embedding_result.embedding)
                            valid_work_items.append(work_item)
            
            if len(embeddings) < 5:
                logger.warning("Not enough embeddings for clustering analysis")
                return []
            
            # Perform clustering
            work_item_metadata = {str(wi.get('id', 'unknown')): {'work_item': wi} for wi in valid_work_items}
            clusters = self.similarity_engine.cluster_work_items(
                embeddings, 
                [str(wi.get('id', 'unknown')) for wi in valid_work_items],
                work_item_metadata
            )
            
            return clusters
        
        except Exception as e:
            logger.error(f"Clustering analysis failed: {str(e)}")
            return []
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector database."""
        stats = self.vector_db.get_stats()
        cache_stats = self.embeddings_client.get_cache_stats()
        
        return {
            "vector_database": {
                "total_vectors": stats.total_vectors,
                "dimension": stats.dimension,
                "index_type": stats.index_type,
                "memory_usage_mb": stats.memory_usage_mb
            },
            "embeddings_cache": cache_stats,
            "config": {
                "similarity_threshold": self.config.vector_db.similarity_threshold,
                "max_results": self.config.vector_db.max_results,
                "clustering_method": self.config.similarity.clustering_method
            }
        }
    
    def clear_database(self):
        """Clear the vector database."""
        self.vector_db.clear_database()
        self.embeddings_client.clear_cache()
        logger.info("Vector database and cache cleared")
    
    def export_analysis_data(self, result: SemanticAnalysisResult, file_path: str) -> bool:
        """Export analysis result to file."""
        try:
            export_data = {
                "work_item_id": result.work_item_id,
                "similar_work_items": [
                    {
                        "work_item_id": sim.work_item_id,
                        "similarity_score": sim.similarity_score,
                        "metadata": sim.metadata
                    }
                    for sim in result.similar_work_items
                ],
                "clusters": [
                    {
                        "cluster_id": cluster.cluster_id,
                        "work_item_ids": cluster.work_item_ids,
                        "size": cluster.size,
                        "avg_similarity": cluster.avg_similarity,
                        "dominant_work_item_type": cluster.dominant_work_item_type,
                        "common_tags": cluster.common_tags
                    }
                    for cluster in result.clusters
                ],
                "relationships": [
                    {
                        "work_item_1_id": rel.work_item_1_id,
                        "work_item_2_id": rel.work_item_2_id,
                        "relationship_type": rel.relationship_type,
                        "confidence_score": rel.confidence_score,
                        "explanation": rel.explanation,
                        "evidence": rel.evidence,
                        "suggested_action": rel.suggested_action,
                        "impact_level": rel.impact_level,
                        "is_automatic_linkable": rel.is_automatic_linkable
                    }
                    for rel in result.relationships
                ],
                "analysis_metadata": result.analysis_metadata,
                "processing_time": result.processing_time,
                "success": result.success,
                "error": result.error,
                "exported_at": datetime.now().isoformat()
            }
            
            with open(file_path, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            logger.info(f"Analysis data exported to {file_path}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to export analysis data: {str(e)}")
            return False

# Synchronous wrapper for easier integration
class SyncSemanticSimilarityEngine:
    """Synchronous wrapper for the semantic similarity engine."""
    
    def __init__(self, config: SemanticSimilarityConfig, openarena_client=None):
        self.config = config
        self.openarena_client = openarena_client
        self._async_engine = SemanticSimilarityEngine(config, openarena_client)
    
    @property
    def vector_db(self):
        """Access to the vector database."""
        return self._async_engine.vector_db
    
    def analyze_work_item(self, work_item: Dict[str, Any], 
                         all_work_items: List[Dict[str, Any]] = None) -> SemanticAnalysisResult:
        """Analyze work item synchronously."""
        async def _async_analyze():
            return await self._async_engine.analyze_work_item(work_item, all_work_items)
        
        return asyncio.run(_async_analyze())
    
    def build_vector_database(self, work_items: List[Dict[str, Any]]) -> bool:
        """Build vector database synchronously."""
        async def _async_build():
            return await self._async_engine.build_vector_database(work_items)
        
        return asyncio.run(_async_build())
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        return self._async_engine.get_database_stats()
    
    def clear_database(self):
        """Clear database."""
        self._async_engine.clear_database()
    
    def export_analysis_data(self, result: SemanticAnalysisResult, file_path: str) -> bool:
        """Export analysis data."""
        return self._async_engine.export_analysis_data(result, file_path)



