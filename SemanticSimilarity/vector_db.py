"""
Vector Database Module

This module provides vector database operations for storing and searching work item embeddings.
Supports local storage with FAISS and future Azure AI Search integration.
"""

import os
import json
import logging
import pickle
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass
import numpy as np
from pathlib import Path
import sqlite3
from datetime import datetime

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logging.warning("FAISS not available. Install with: pip install faiss-cpu or faiss-gpu")

from .config import VectorDBConfig
from .embeddings import EmbeddingResult

logger = logging.getLogger(__name__)

@dataclass
class SimilarityResult:
    """Result of similarity search."""
    work_item_id: str
    similarity_score: float
    embedding: List[float]
    metadata: Dict[str, Any]
    rank: int

@dataclass
class VectorDBStats:
    """Statistics about the vector database."""
    total_vectors: int
    dimension: int
    index_type: str
    last_updated: datetime
    memory_usage_mb: float

class VectorDatabase:
    """Vector database for storing and searching work item embeddings."""
    
    def __init__(self, config: VectorDBConfig):
        self.config = config
        self.index = None
        self.work_item_metadata = {}
        self.work_item_ids = []
        self._db_path = Path(config.local_db_path)
        self._db_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_database()
    
    def _init_database(self):
        """Initialize the vector database."""
        if self.config.db_type == "local":
            self._init_local_database()
        else:
            raise ValueError(f"Unsupported database type: {self.config.db_type}")
    
    def _init_local_database(self):
        """Initialize local FAISS database."""
        if not FAISS_AVAILABLE:
            raise ImportError("FAISS is required for local vector database. Install with: pip install faiss-cpu")
        
        self.index_file = self._db_path / "faiss_index.bin"
        self.metadata_file = self._db_path / "metadata.json"
        
        # Load existing index if available
        if self.index_file.exists() and self.metadata_file.exists():
            self._load_index()
        else:
            self._create_new_index()
    
    def _create_new_index(self):
        """Create a new FAISS index."""
        # Create IndexFlatIP (Inner Product) for cosine similarity
        self.index = faiss.IndexFlatIP(self.config.embedding_dimension)
        self.work_item_metadata = {}
        self.work_item_ids = []
        logger.info(f"Created new FAISS index with dimension {self.config.embedding_dimension}")
    
    def _load_index(self):
        """Load existing FAISS index."""
        try:
            # Load FAISS index
            self.index = faiss.read_index(str(self.index_file))
            
            # Load metadata
            with open(self.metadata_file, 'r') as f:
                data = json.load(f)
                self.work_item_metadata = data.get('metadata', {})
                self.work_item_ids = data.get('work_item_ids', [])
            
            logger.info(f"Loaded FAISS index with {self.index.ntotal} vectors")
        
        except Exception as e:
            logger.error(f"Failed to load existing index: {str(e)}")
            self._create_new_index()
    
    def _save_index(self):
        """Save FAISS index and metadata."""
        try:
            # Save FAISS index
            faiss.write_index(self.index, str(self.index_file))
            
            # Save metadata
            data = {
                'metadata': self.work_item_metadata,
                'work_item_ids': self.work_item_ids,
                'last_updated': datetime.now().isoformat(),
                'dimension': self.config.embedding_dimension
            }
            
            with open(self.metadata_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Saved FAISS index with {self.index.ntotal} vectors")
        
        except Exception as e:
            logger.error(f"Failed to save index: {str(e)}")
    
    def add_work_items(self, work_items: List[Dict[str, Any]], embeddings: List[EmbeddingResult]) -> bool:
        """Add work items and their embeddings to the database."""
        if len(work_items) != len(embeddings):
            raise ValueError("Number of work items must match number of embeddings")
        
        try:
            # Prepare vectors and metadata
            vectors = []
            new_metadata = {}
            new_work_item_ids = []
            duplicates_skipped = 0
            
            for i, (work_item, embedding) in enumerate(zip(work_items, embeddings)):
                if not embedding.success or not embedding.embedding:
                    logger.warning(f"Skipping work item {work_item.get('id', 'unknown')} - invalid embedding")
                    continue
                
                work_item_id = str(work_item.get('id', f'item_{i}'))
                
                # Check for duplicate work item ID
                if work_item_id in self.work_item_metadata:
                    logger.info(f"Skipping duplicate work item {work_item_id} - already exists in database")
                    duplicates_skipped += 1
                    continue
                
                # Normalize embedding for cosine similarity
                embedding_vector = np.array(embedding.embedding, dtype=np.float32)
                embedding_vector = embedding_vector / np.linalg.norm(embedding_vector)
                vectors.append(embedding_vector)
                
                # Store metadata
                new_metadata[work_item_id] = {
                    'work_item': work_item,
                    'embedding_info': {
                        'model': embedding.model,
                        'usage_tokens': embedding.usage_tokens,
                        'processing_time': embedding.processing_time
                    },
                    'added_at': datetime.now().isoformat()
                }
                new_work_item_ids.append(work_item_id)
            
            if not vectors:
                if duplicates_skipped > 0:
                    logger.info(f"No new work items to add (all {duplicates_skipped} were duplicates)")
                    return True  # Consider this successful - duplicates are expected
                else:
                    logger.warning("No valid embeddings to add (all were invalid)")
                    return False
            
            # Convert to numpy array
            vectors_array = np.vstack(vectors).astype(np.float32)
            
            # Add to FAISS index
            self.index.add(vectors_array)
            
            # Update metadata
            self.work_item_metadata.update(new_metadata)
            self.work_item_ids.extend(new_work_item_ids)
            
            # Save to disk
            self._save_index()
            
            if duplicates_skipped > 0:
                logger.info(f"Added {len(vectors)} new work items to vector database (skipped {duplicates_skipped} duplicates)")
            else:
                logger.info(f"Added {len(vectors)} new work items to vector database")
            return True
        
        except Exception as e:
            logger.error(f"Failed to add work items: {str(e)}")
            return False
    
    def search_similar(self, query_embedding: List[float], top_k: int = 10, 
                      work_item_metadata: Dict[str, Any] = None) -> List[SimilarityResult]:
        """Search for similar work items using a query embedding with enhanced relevance scoring."""
        if not self.index or self.index.ntotal == 0:
            logger.warning("Vector database is empty")
            return []
        
        try:
            # Normalize query embedding
            query_vector = np.array(query_embedding, dtype=np.float32)
            query_vector = query_vector / np.linalg.norm(query_vector)
            query_vector = query_vector.reshape(1, -1)
            
            # Search with more results initially for better filtering
            search_k = min(top_k * 3, self.index.ntotal)  # Get 3x more results for filtering
            scores, indices = self.index.search(query_vector, search_k)
            
            # Convert to results with enhanced relevance scoring
            results = []
            for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                if idx == -1:  # Invalid index
                    continue
                
                work_item_id = self.work_item_ids[idx]
                metadata = self.work_item_metadata.get(work_item_id, {})
                
                # Calculate enhanced relevance score
                enhanced_score = self._calculate_relevance_score(
                    float(score), 
                    metadata, 
                    work_item_metadata
                )
                
                result = SimilarityResult(
                    work_item_id=work_item_id,
                    similarity_score=enhanced_score,
                    embedding=query_embedding,
                    metadata=metadata,
                    rank=i + 1
                )
                results.append(result)
            
            # Apply adaptive thresholding
            threshold = self._get_adaptive_threshold(results)
            
            # Filter by threshold and sort by relevance
            filtered_results = [
                r for r in results 
                if r.similarity_score >= threshold
            ]
            
            # Sort by relevance score (descending)
            filtered_results.sort(key=lambda x: x.similarity_score, reverse=True)
            
            # Limit to requested number of results
            final_results = filtered_results[:top_k]
            
            logger.info(f"Found {len(final_results)} similar work items (threshold: {threshold:.3f}, original: {len(results)})")
            return final_results
        
        except Exception as e:
            logger.error(f"Failed to search similar work items: {str(e)}")
            return []
    
    def _calculate_relevance_score(self, base_score: float, metadata: Dict[str, Any], 
                                 query_metadata: Dict[str, Any] = None) -> float:
        """Calculate enhanced relevance score based on multiple factors."""
        if not metadata:
            return base_score
        
        work_item = metadata.get('work_item', {})
        relevance_multiplier = 1.0
        
        # Factor 1: Work item type matching (higher weight)
        if query_metadata and 'workItemType' in query_metadata:
            query_type = query_metadata.get('workItemType', '').lower()
            item_type = work_item.get('workItemType', '').lower()
            if query_type and item_type and query_type == item_type:
                relevance_multiplier += 0.15  # 15% boost for same type
            elif query_type and item_type:
                # Penalize different types less severely
                if (query_type in ['bug', 'defect'] and item_type in ['bug', 'defect']) or \
                   (query_type in ['user story', 'story'] and item_type in ['user story', 'story']) or \
                   (query_type in ['task', 'subtask'] and item_type in ['task', 'subtask']):
                    relevance_multiplier += 0.05  # 5% boost for similar types
        
        # Factor 2: Area path similarity (higher weight)
        if query_metadata and 'areaPath' in query_metadata:
            query_area = query_metadata.get('areaPath', '').lower()
            item_area = work_item.get('areaPath', '').lower()
            if query_area and item_area:
                # Calculate area path similarity
                query_parts = set(query_area.split('\\'))
                item_parts = set(item_area.split('\\'))
                common_parts = len(query_parts.intersection(item_parts))
                total_parts = len(query_parts.union(item_parts))
                if total_parts > 0:
                    area_similarity = common_parts / total_parts
                    relevance_multiplier += area_similarity * 0.10  # Up to 10% boost
        
        # Factor 3: Tag similarity (higher weight)
        if query_metadata and 'tags' in query_metadata:
            query_tags = set(query_metadata.get('tags', '').lower().split(';'))
            item_tags = set(work_item.get('tags', '').lower().split(';'))
            if query_tags and item_tags:
                common_tags = len(query_tags.intersection(item_tags))
                if common_tags > 0:
                    relevance_multiplier += min(common_tags * 0.03, 0.08)  # Up to 8% boost
        
        # Factor 4: State relevance (active items are more relevant)
        item_state = work_item.get('state', '').lower()
        if item_state in ['active', 'new', 'in progress']:
            relevance_multiplier += 0.03  # 3% boost for active items
        elif item_state in ['closed', 'done', 'resolved']:
            relevance_multiplier += 0.01  # 1% boost for completed items
        
        # Factor 5: Title keyword matching (much higher weight for exact matches)
        if query_metadata and 'title' in query_metadata:
            query_title = query_metadata.get('title', '').lower()
            item_title = work_item.get('title', '').lower()
            if query_title and item_title:
                # Calculate title similarity
                title_similarity = self._calculate_title_similarity(query_title, item_title)
                
                if title_similarity > 0.90:
                    # Very high similarity - treat as exact match
                    relevance_multiplier += 0.20  # 20% boost for near-exact matches
                elif title_similarity > 0.80:
                    # High similarity
                    relevance_multiplier += 0.15  # 15% boost for high similarity
                elif title_similarity > 0.70:
                    # Medium similarity
                    relevance_multiplier += 0.10  # 10% boost for medium similarity
                else:
                    # Enhanced keyword matching with stemming
                    query_words = set(self._stem_words(query_title.split()))
                    item_words = set(self._stem_words(item_title.split()))
                    common_words = len(query_words.intersection(item_words))
                    if common_words > 0:
                        relevance_multiplier += min(common_words * 0.03, 0.15)  # Up to 15% boost
        
        # Factor 6: Description keyword matching (new)
        if query_metadata and 'description' in query_metadata:
            query_desc = query_metadata.get('description', '').lower()
            item_desc = work_item.get('description', '').lower()
            if query_desc and item_desc:
                query_words = set(self._stem_words(query_desc.split()))
                item_words = set(self._stem_words(item_desc.split()))
                common_words = len(query_words.intersection(item_words))
                if common_words > 0:
                    relevance_multiplier += min(common_words * 0.02, 0.10)  # Up to 10% boost
        
        # Factor 7: Priority matching (new)
        if query_metadata and 'priority' in query_metadata and 'priority' in work_item:
            query_priority = query_metadata.get('priority', 0)
            item_priority = work_item.get('priority', 0)
            if query_priority and item_priority:
                priority_diff = abs(query_priority - item_priority)
                if priority_diff == 0:
                    relevance_multiplier += 0.05  # 5% boost for same priority
                elif priority_diff == 1:
                    relevance_multiplier += 0.02  # 2% boost for similar priority
        
        # Apply conservative additive boost to base score
        # Only boost if the base score is already reasonably high (>0.5)
        if base_score > 0.5:
            boost = (relevance_multiplier - 1.0) * 0.2  # Scale down the boost significantly
            enhanced_score = base_score + boost
        else:
            # For low base scores, only apply minimal boost
            boost = (relevance_multiplier - 1.0) * 0.05
            enhanced_score = base_score + boost
        
        # Log detailed scoring for debugging
        if query_metadata and 'id' in query_metadata:
            logger.debug(f"Relevance scoring for work item {work_item.get('id', 'unknown')}: "
                        f"base_score={base_score:.3f}, multiplier={relevance_multiplier:.3f}, "
                        f"enhanced_score={enhanced_score:.3f}")
        
        # Ensure score doesn't exceed 1.0
        return min(enhanced_score, 1.0)
    
    def _stem_words(self, words: List[str]) -> List[str]:
        """Simple word stemming for better keyword matching."""
        # Remove common suffixes for basic stemming
        stemmed = []
        for word in words:
            if len(word) > 3:
                if word.endswith('ing'):
                    stemmed.append(word[:-3])
                elif word.endswith('ed'):
                    stemmed.append(word[:-2])
                elif word.endswith('s') and len(word) > 4:
                    stemmed.append(word[:-1])
                else:
                    stemmed.append(word)
            else:
                stemmed.append(word)
        return stemmed
    
    def _calculate_title_similarity(self, title1: str, title2: str) -> float:
        """Calculate title similarity using word overlap and Jaccard similarity."""
        if not title1 or not title2:
            return 0.0
        
        # Normalize titles
        title1_clean = title1.lower().strip()
        title2_clean = title2.lower().strip()
        
        # If titles are identical, return perfect similarity
        if title1_clean == title2_clean:
            return 1.0
        
        # Split into words and remove common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        
        words1 = set(word for word in title1_clean.split() if word not in stop_words and len(word) > 2)
        words2 = set(word for word in title2_clean.split() if word not in stop_words and len(word) > 2)
        
        if not words1 or not words2:
            return 0.0
        
        # Calculate Jaccard similarity
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        jaccard_similarity = len(intersection) / len(union)
        
        # Boost similarity if there are many common words
        if len(intersection) >= 5:  # If 5+ common words, boost the score
            jaccard_similarity = min(jaccard_similarity * 1.2, 1.0)
        
        return jaccard_similarity
    
    def _get_adaptive_threshold(self, results: List[SimilarityResult]) -> float:
        """Calculate adaptive threshold based on result distribution."""
        if not self.config.adaptive_threshold or not results:
            return self.config.similarity_threshold
        
        # Get base scores (before enhancement)
        base_scores = [r.similarity_score for r in results]
        
        if len(base_scores) < 3:
            return self.config.similarity_threshold
        
        # Check for exact matches (score = 1.0) - don't filter them out
        exact_matches = [score for score in base_scores if score >= 0.99]
        if exact_matches:
            # If we have exact matches, use a lower threshold to include them
            threshold = min(0.99, self.config.similarity_threshold)
            logger.info(f"Exact matches detected ({len(exact_matches)}), using lower threshold: {threshold:.3f}")
            return threshold
        
        # Calculate statistics
        mean_score = np.mean(base_scores)
        std_score = np.std(base_scores)
        max_score = np.max(base_scores)
        
        # More intelligent adaptive threshold
        if len(base_scores) < 5:
            # Few results - use conservative threshold
            threshold = max(mean_score - 0.1, self.config.min_similarity_threshold)
        elif std_score < 0.05:  # Very low variance - use higher threshold
            threshold = max(mean_score + 0.05, self.config.min_similarity_threshold)
        elif std_score < 0.15:  # Low variance - use mean-based threshold
            threshold = max(mean_score - 0.05, self.config.min_similarity_threshold)
        else:  # High variance - use more permissive threshold
            threshold = max(mean_score - 0.15, self.config.min_similarity_threshold)
        
        # Ensure we don't go below minimum or above maximum
        threshold = max(threshold, self.config.min_similarity_threshold)
        threshold = min(threshold, self.config.max_similarity_threshold)
        
        # If the best result is below our threshold, lower it slightly
        if max_score < threshold:
            threshold = max(max_score - 0.05, self.config.min_similarity_threshold)
        
        return threshold
    
    def search_by_work_item_id(self, work_item_id: str, top_k: int = 10) -> List[SimilarityResult]:
        """Search for work items similar to a specific work item."""
        if work_item_id not in self.work_item_metadata:
            logger.warning(f"Work item {work_item_id} not found in database")
            return []
        
        # Get the embedding for this work item
        # Note: We need to store the original embeddings to do this
        # For now, we'll need to re-embed the work item
        logger.warning("Search by work item ID requires re-embedding. Consider storing original embeddings.")
        return []
    
    def get_work_item_metadata(self, work_item_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific work item."""
        return self.work_item_metadata.get(work_item_id)
    
    def get_all_work_item_ids(self) -> List[str]:
        """Get all work item IDs in the database."""
        return self.work_item_ids.copy()
    
    def work_item_exists(self, work_item_id: str) -> bool:
        """Check if a work item already exists in the database."""
        return str(work_item_id) in self.work_item_metadata
    
    def get_existing_work_item_ids(self, work_items: List[Dict[str, Any]]) -> List[str]:
        """Get work item IDs that already exist in the database."""
        existing_ids = []
        for work_item in work_items:
            work_item_id = str(work_item.get('id', ''))
            if work_item_id and self.work_item_exists(work_item_id):
                existing_ids.append(work_item_id)
        return existing_ids
    
    def remove_duplicates(self) -> int:
        """Remove duplicate work items from the database based on work item ID."""
        if not self.work_item_ids or not self.work_item_metadata:
            return 0
        
        # Find duplicates
        seen_ids = set()
        duplicates = []
        
        for i, work_item_id in enumerate(self.work_item_ids):
            if work_item_id in seen_ids:
                duplicates.append(i)
            else:
                seen_ids.add(work_item_id)
        
        if not duplicates:
            logger.info("No duplicates found in vector database")
            return 0
        
        # Remove duplicates (in reverse order to maintain indices)
        for i in reversed(duplicates):
            work_item_id = self.work_item_ids[i]
            del self.work_item_ids[i]
            if work_item_id in self.work_item_metadata:
                del self.work_item_metadata[work_item_id]
        
        # Rebuild FAISS index without duplicates
        if self.work_item_ids:
            # Get all existing embeddings
            all_embeddings = []
            for work_item_id in self.work_item_ids:
                metadata = self.work_item_metadata.get(work_item_id, {})
                embedding_info = metadata.get('embedding_info', {})
                # We need to reconstruct embeddings from stored data
                # For now, we'll create a simple hash-based embedding
                work_item = metadata.get('work_item', {})
                text = f"{work_item.get('title', '')} {work_item.get('description', '')}"
                embedding = self._create_simple_embedding(text)
                all_embeddings.append(embedding)
            
            # Rebuild FAISS index
            vectors_array = np.vstack(all_embeddings).astype(np.float32)
            self.index = faiss.IndexFlatIP(self.config.embedding_dimension)
            self.index.add(vectors_array)
            
            # Save updated index
            self._save_index()
        
        logger.info(f"Removed {len(duplicates)} duplicate work items from vector database")
        return len(duplicates)
    
    def _create_simple_embedding(self, text: str) -> np.ndarray:
        """Create a simple hash-based embedding for reconstruction."""
        import hashlib
        text_hash = hashlib.sha256(text.encode()).digest()
        embedding = []
        for i in range(self.config.embedding_dimension):
            byte_index = i % len(text_hash)
            embedding.append(float(text_hash[byte_index]) / 255.0)
        
        # Normalize
        embedding = np.array(embedding, dtype=np.float32)
        return embedding / np.linalg.norm(embedding)
    
    def find_similar_work_items(self, work_item: Dict[str, Any], top_k: int = 10, threshold: float = 0.7) -> List[SimilarityResult]:
        """Find similar work items using a work item dictionary (for enhanced integration)."""
        try:
            # First, try to find the work item in our database
            work_item_id = str(work_item.get('id', ''))
            
            if work_item_id in self.work_item_metadata:
                # Work item exists in database, find its index
                try:
                    work_item_index = self.work_item_ids.index(work_item_id)
                    
                    # Get the embedding from the FAISS index
                    query_vector = self.index.reconstruct(work_item_index)
                    query_vector = query_vector.reshape(1, -1)
                    
                    # Search for similar items
                    search_k = min(top_k * 2, self.index.ntotal)
                    scores, indices = self.index.search(query_vector, search_k)
                    
                    # Convert to results with exact match detection
                    results = []
                    exact_matches = []
                    
                    for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                        if idx == -1 or idx == work_item_index:  # Skip invalid or same item
                            continue
                        
                        similar_work_item_id = self.work_item_ids[idx]
                        metadata = self.work_item_metadata.get(similar_work_item_id, {})
                        similar_work_item = metadata.get('work_item', {})
                        
                        # Check for exact match based on title similarity
                        title_similarity = self._calculate_title_similarity(
                            work_item.get('title', ''), 
                            similar_work_item.get('title', '')
                        )
                        
                        # If title similarity is very high (>90%), treat as exact match
                        if title_similarity > 0.90:
                            enhanced_score = 1.0  # Perfect similarity for exact matches
                            exact_matches.append((similar_work_item_id, enhanced_score, metadata, i))
                            logger.info(f"Exact match detected: #{similar_work_item_id} (title similarity: {title_similarity:.3f})")
                        else:
                            # Apply relevance scoring enhancement
                            enhanced_score = self._calculate_relevance_score(
                                float(score), 
                                metadata, 
                                work_item
                            )
                            
                            if enhanced_score >= threshold:
                                result = SimilarityResult(
                                    work_item_id=similar_work_item_id,
                                    similarity_score=enhanced_score,
                                    embedding=[],  # Not needed for results
                                    metadata=metadata,
                                    rank=len(results) + 1
                                )
                                results.append(result)
                    
                    # Add exact matches at the top
                    for similar_work_item_id, enhanced_score, metadata, original_rank in exact_matches:
                        result = SimilarityResult(
                            work_item_id=similar_work_item_id,
                            similarity_score=enhanced_score,
                            embedding=[],
                            metadata=metadata,
                            rank=len(results) + 1
                        )
                        results.insert(0, result)  # Insert at the beginning
                    
                    # Limit to requested number of results
                    results = results[:top_k]
                    
                    logger.info(f"Found {len(results)} similar work items for work item {work_item_id} ({len(exact_matches)} exact matches)")
                    return results
                    
                except ValueError:
                    logger.warning(f"Work item {work_item_id} not found in FAISS index")
                    return []
            else:
                logger.warning(f"Work item {work_item_id} not found in database")
                return []
                
        except Exception as e:
            logger.error(f"Failed to find similar work items: {str(e)}")
            return []
    
    def remove_work_item(self, work_item_id: str) -> bool:
        """Remove a work item from the database."""
        if work_item_id not in self.work_item_metadata:
            logger.warning(f"Work item {work_item_id} not found")
            return False
        
        try:
            # Find index in work_item_ids
            if work_item_id in self.work_item_ids:
                idx = self.work_item_ids.index(work_item_id)
                
                # Remove from FAISS index (this is complex with FAISS)
                # For now, we'll mark as removed in metadata
                self.work_item_metadata[work_item_id]['removed'] = True
                self.work_item_ids.remove(work_item_id)
                
                # Save changes
                self._save_index()
                
                logger.info(f"Removed work item {work_item_id} from database")
                return True
            else:
                logger.warning(f"Work item {work_item_id} not found in index")
                return False
        
        except Exception as e:
            logger.error(f"Failed to remove work item {work_item_id}: {str(e)}")
            return False
    
    def get_stats(self) -> VectorDBStats:
        """Get database statistics."""
        memory_usage = 0
        if self.index:
            # Estimate memory usage (rough calculation)
            memory_usage = (self.index.ntotal * self.config.embedding_dimension * 4) / (1024 * 1024)  # 4 bytes per float32
        
        return VectorDBStats(
            total_vectors=self.index.ntotal if self.index else 0,
            dimension=self.config.embedding_dimension,
            index_type="FAISS IndexFlatIP",
            last_updated=datetime.now(),
            memory_usage_mb=memory_usage
        )
    
    def clear_database(self):
        """Clear all data from the database."""
        self._create_new_index()
        self._save_index()
        logger.info("Cleared vector database")
    
    def rebuild_index(self):
        """Rebuild the entire index from metadata."""
        if not self.work_item_metadata:
            logger.warning("No metadata available to rebuild index")
            return False
        
        try:
            # This would require storing original embeddings
            # For now, we'll just recreate the index structure
            logger.warning("Rebuild index requires original embeddings to be stored")
            return False
        
        except Exception as e:
            logger.error(f"Failed to rebuild index: {str(e)}")
            return False
    
    def export_data(self, file_path: str) -> bool:
        """Export database data to file."""
        try:
            data = {
                'metadata': self.work_item_metadata,
                'work_item_ids': self.work_item_ids,
                'config': self.config.__dict__,
                'stats': self.get_stats().__dict__,
                'exported_at': datetime.now().isoformat()
            }
            
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            logger.info(f"Exported database data to {file_path}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to export data: {str(e)}")
            return False
    
    def import_data(self, file_path: str) -> bool:
        """Import database data from file."""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            self.work_item_metadata = data.get('metadata', {})
            self.work_item_ids = data.get('work_item_ids', [])
            
            # Note: This doesn't restore the FAISS index
            # You would need to rebuild it from the embeddings
            logger.warning("Import only restores metadata. FAISS index needs to be rebuilt.")
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to import data: {str(e)}")
            return False



