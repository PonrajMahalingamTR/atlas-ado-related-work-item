"""
Similarity Engine Module

This module provides similarity calculation and clustering algorithms for work items.
Supports various similarity metrics and clustering methods.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass
import numpy as np
from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering
from sklearn.metrics.pairwise import cosine_similarity, euclidean_distances
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
import matplotlib.pyplot as plt
from collections import defaultdict

from .config import SimilarityConfig
from .vector_db import SimilarityResult

logger = logging.getLogger(__name__)

@dataclass
class ClusterResult:
    """Result of clustering analysis."""
    cluster_id: int
    work_item_ids: List[str]
    centroid: List[float]
    size: int
    avg_similarity: float
    dominant_work_item_type: str
    common_tags: List[str]

@dataclass
class SimilarityAnalysis:
    """Comprehensive similarity analysis result."""
    similarity_matrix: np.ndarray
    clusters: List[ClusterResult]
    similarity_pairs: List[Tuple[str, str, float]]
    statistics: Dict[str, Any]

class SimilarityEngine:
    """Engine for calculating similarities and performing clustering analysis."""
    
    def __init__(self, config: SimilarityConfig):
        self.config = config
        self.similarity_cache = {}
    
    def calculate_similarity_matrix(self, embeddings: List[List[float]], 
                                  work_item_ids: List[str]) -> np.ndarray:
        """Calculate pairwise similarity matrix for embeddings."""
        if not embeddings or not work_item_ids:
            return np.array([])
        
        embeddings_array = np.array(embeddings)
        
        if self.config.algorithm == "cosine":
            similarity_matrix = cosine_similarity(embeddings_array)
        elif self.config.algorithm == "euclidean":
            # Convert distance to similarity (1 - normalized distance)
            distances = euclidean_distances(embeddings_array)
            max_distance = np.max(distances)
            similarity_matrix = 1 - (distances / max_distance)
        elif self.config.algorithm == "dot_product":
            similarity_matrix = np.dot(embeddings_array, embeddings_array.T)
        else:
            raise ValueError(f"Unsupported similarity algorithm: {self.config.algorithm}")
        
        # Ensure diagonal is 1.0 (self-similarity)
        np.fill_diagonal(similarity_matrix, 1.0)
        
        logger.info(f"Calculated {self.config.algorithm} similarity matrix: {similarity_matrix.shape}")
        return similarity_matrix
    
    def find_similar_pairs(self, similarity_matrix: np.ndarray, 
                          work_item_ids: List[str], 
                          threshold: float = None) -> List[Tuple[str, str, float]]:
        """Find pairs of work items above similarity threshold."""
        if threshold is None:
            threshold = self.config.confidence_levels["low"]
        
        pairs = []
        n = len(work_item_ids)
        
        for i in range(n):
            for j in range(i + 1, n):
                similarity = similarity_matrix[i, j]
                if similarity >= threshold:
                    pairs.append((work_item_ids[i], work_item_ids[j], similarity))
        
        # Sort by similarity score (descending)
        pairs.sort(key=lambda x: x[2], reverse=True)
        
        logger.info(f"Found {len(pairs)} similar pairs above threshold {threshold}")
        return pairs
    
    def cluster_work_items(self, embeddings: List[List[float]], 
                          work_item_ids: List[str],
                          work_item_metadata: Dict[str, Dict[str, Any]]) -> List[ClusterResult]:
        """Cluster work items based on their embeddings."""
        if not embeddings or not work_item_ids:
            return []
        
        embeddings_array = np.array(embeddings)
        
        try:
            if self.config.clustering_method == "kmeans":
                clusters = self._kmeans_clustering(embeddings_array, work_item_ids, work_item_metadata)
            elif self.config.clustering_method == "dbscan":
                clusters = self._dbscan_clustering(embeddings_array, work_item_ids, work_item_metadata)
            elif self.config.clustering_method == "hierarchical":
                clusters = self._hierarchical_clustering(embeddings_array, work_item_ids, work_item_metadata)
            else:
                raise ValueError(f"Unsupported clustering method: {self.config.clustering_method}")
            
            logger.info(f"Created {len(clusters)} clusters using {self.config.clustering_method}")
            return clusters
        
        except Exception as e:
            logger.error(f"Clustering failed: {str(e)}")
            return []
    
    def _kmeans_clustering(self, embeddings: np.ndarray, 
                          work_item_ids: List[str],
                          work_item_metadata: Dict[str, Dict[str, Any]]) -> List[ClusterResult]:
        """Perform K-means clustering."""
        n_clusters = min(self.config.n_clusters, len(work_item_ids))
        
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(embeddings)
        
        return self._create_cluster_results(
            cluster_labels, embeddings, work_item_ids, work_item_metadata, kmeans.cluster_centers_
        )
    
    def _dbscan_clustering(self, embeddings: np.ndarray, 
                          work_item_ids: List[str],
                          work_item_metadata: Dict[str, Dict[str, Any]]) -> List[ClusterResult]:
        """Perform DBSCAN clustering."""
        dbscan = DBSCAN(eps=0.5, min_samples=self.config.min_cluster_size)
        cluster_labels = dbscan.fit_predict(embeddings)
        
        # Get cluster centers (mean of points in each cluster)
        unique_labels = set(cluster_labels)
        cluster_centers = []
        
        for label in unique_labels:
            if label == -1:  # Noise points
                continue
            mask = cluster_labels == label
            center = np.mean(embeddings[mask], axis=0)
            cluster_centers.append(center)
        
        return self._create_cluster_results(
            cluster_labels, embeddings, work_item_ids, work_item_metadata, cluster_centers
        )
    
    def _hierarchical_clustering(self, embeddings: np.ndarray, 
                                work_item_ids: List[str],
                                work_item_metadata: Dict[str, Dict[str, Any]]) -> List[ClusterResult]:
        """Perform hierarchical clustering."""
        n_clusters = min(self.config.n_clusters, len(work_item_ids))
        
        hierarchical = AgglomerativeClustering(n_clusters=n_clusters)
        cluster_labels = hierarchical.fit_predict(embeddings)
        
        # Get cluster centers (mean of points in each cluster)
        unique_labels = set(cluster_labels)
        cluster_centers = []
        
        for label in unique_labels:
            mask = cluster_labels == label
            center = np.mean(embeddings[mask], axis=0)
            cluster_centers.append(center)
        
        return self._create_cluster_results(
            cluster_labels, embeddings, work_item_ids, work_item_metadata, cluster_centers
        )
    
    def _create_cluster_results(self, cluster_labels: np.ndarray, 
                               embeddings: np.ndarray,
                               work_item_ids: List[str],
                               work_item_metadata: Dict[str, Dict[str, Any]],
                               cluster_centers: List[np.ndarray]) -> List[ClusterResult]:
        """Create ClusterResult objects from clustering results."""
        clusters = []
        unique_labels = set(cluster_labels)
        
        for i, label in enumerate(unique_labels):
            if label == -1:  # Skip noise points in DBSCAN
                continue
            
            # Get work items in this cluster
            mask = cluster_labels == label
            cluster_work_item_ids = [work_item_ids[j] for j in range(len(work_item_ids)) if mask[j]]
            
            if len(cluster_work_item_ids) < self.config.min_cluster_size:
                continue
            
            # Calculate average similarity within cluster
            cluster_embeddings = embeddings[mask]
            if len(cluster_embeddings) > 1:
                similarity_matrix = cosine_similarity(cluster_embeddings)
                # Get upper triangle (excluding diagonal)
                upper_triangle = similarity_matrix[np.triu_indices_from(similarity_matrix, k=1)]
                avg_similarity = np.mean(upper_triangle)
            else:
                avg_similarity = 1.0
            
            # Analyze cluster characteristics
            work_item_types = []
            all_tags = []
            
            for work_item_id in cluster_work_item_ids:
                metadata = work_item_metadata.get(work_item_id, {})
                work_item = metadata.get('work_item', {})
                
                # Extract work item type
                if 'workItemType' in work_item:
                    work_item_types.append(work_item['workItemType'])
                elif 'fields' in work_item and 'System.WorkItemType' in work_item['fields']:
                    work_item_types.append(work_item['fields']['System.WorkItemType'])
                
                # Extract tags
                if 'tags' in work_item:
                    tags = work_item['tags'].split(';') if isinstance(work_item['tags'], str) else work_item['tags']
                    all_tags.extend([tag.strip() for tag in tags if tag.strip()])
                elif 'fields' in work_item and 'System.Tags' in work_item['fields']:
                    tags = work_item['fields']['System.Tags'].split(';') if work_item['fields']['System.Tags'] else []
                    all_tags.extend([tag.strip() for tag in tags if tag.strip()])
            
            # Find dominant work item type
            if work_item_types:
                type_counts = defaultdict(int)
                for work_type in work_item_types:
                    type_counts[work_type] += 1
                dominant_type = max(type_counts, key=type_counts.get)
            else:
                dominant_type = "Unknown"
            
            # Find common tags
            if all_tags:
                tag_counts = defaultdict(int)
                for tag in all_tags:
                    tag_counts[tag] += 1
                # Get tags that appear in at least 2 items
                common_tags = [tag for tag, count in tag_counts.items() if count >= 2]
                common_tags.sort(key=lambda x: tag_counts[x], reverse=True)
            else:
                common_tags = []
            
            # Get cluster center
            center = cluster_centers[i] if i < len(cluster_centers) else np.mean(cluster_embeddings, axis=0)
            
            cluster_result = ClusterResult(
                cluster_id=label,
                work_item_ids=cluster_work_item_ids,
                centroid=center.tolist(),
                size=len(cluster_work_item_ids),
                avg_similarity=float(avg_similarity),
                dominant_work_item_type=dominant_type,
                common_tags=common_tags[:5]  # Top 5 common tags
            )
            
            clusters.append(cluster_result)
        
        # Sort clusters by size (descending)
        clusters.sort(key=lambda x: x.size, reverse=True)
        
        return clusters
    
    def analyze_similarity_patterns(self, similarity_matrix: np.ndarray, 
                                  work_item_ids: List[str],
                                  work_item_metadata: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze patterns in similarity matrix."""
        if similarity_matrix.size == 0:
            return {}
        
        # Basic statistics
        n = len(work_item_ids)
        upper_triangle = similarity_matrix[np.triu_indices_from(similarity_matrix, k=1)]
        
        stats = {
            "total_pairs": len(upper_triangle),
            "mean_similarity": float(np.mean(upper_triangle)),
            "median_similarity": float(np.median(upper_triangle)),
            "std_similarity": float(np.std(upper_triangle)),
            "min_similarity": float(np.min(upper_triangle)),
            "max_similarity": float(np.max(upper_triangle)),
            "high_similarity_pairs": int(np.sum(upper_triangle >= self.config.confidence_levels["high"])),
            "medium_similarity_pairs": int(np.sum((upper_triangle >= self.config.confidence_levels["medium"]) & 
                                                 (upper_triangle < self.config.confidence_levels["high"]))),
            "low_similarity_pairs": int(np.sum((upper_triangle >= self.config.confidence_levels["low"]) & 
                                              (upper_triangle < self.config.confidence_levels["medium"])))
        }
        
        # Work item type analysis
        work_item_types = defaultdict(list)
        for i, work_item_id in enumerate(work_item_ids):
            metadata = work_item_metadata.get(work_item_id, {})
            work_item = metadata.get('work_item', {})
            
            work_type = "Unknown"
            if 'workItemType' in work_item:
                work_type = work_item['workItemType']
            elif 'fields' in work_item and 'System.WorkItemType' in work_item['fields']:
                work_type = work_item['fields']['System.WorkItemType']
            
            work_item_types[work_type].append(i)
        
        # Calculate average similarity within and between work item types
        type_similarities = {}
        for work_type, indices in work_item_types.items():
            if len(indices) < 2:
                continue
            
            # Within-type similarity
            within_similarities = []
            for i in range(len(indices)):
                for j in range(i + 1, len(indices)):
                    sim = similarity_matrix[indices[i], indices[j]]
                    within_similarities.append(sim)
            
            type_similarities[work_type] = {
                "count": len(indices),
                "avg_within_similarity": float(np.mean(within_similarities)) if within_similarities else 0.0
            }
        
        stats["work_item_type_analysis"] = type_similarities
        
        return stats
    
    def visualize_similarity_matrix(self, similarity_matrix: np.ndarray, 
                                  work_item_ids: List[str],
                                  output_path: str = None) -> str:
        """Create visualization of similarity matrix."""
        if similarity_matrix.size == 0:
            return ""
        
        plt.figure(figsize=(10, 8))
        plt.imshow(similarity_matrix, cmap='viridis', aspect='auto')
        plt.colorbar(label='Similarity Score')
        plt.title('Work Item Similarity Matrix')
        plt.xlabel('Work Item Index')
        plt.ylabel('Work Item Index')
        
        # Add work item IDs as tick labels (sample every 5th)
        n = len(work_item_ids)
        if n <= 20:
            plt.xticks(range(n), work_item_ids, rotation=45)
            plt.yticks(range(n), work_item_ids)
        else:
            step = max(1, n // 10)
            indices = range(0, n, step)
            plt.xticks(indices, [work_item_ids[i] for i in indices], rotation=45)
            plt.yticks(indices, [work_item_ids[i] for i in indices])
        
        plt.tight_layout()
        
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            logger.info(f"Similarity matrix visualization saved to {output_path}")
        
        return output_path or "similarity_matrix.png"
    
    def reduce_dimensions(self, embeddings: List[List[float]], 
                         method: str = "pca", 
                         n_components: int = 2) -> np.ndarray:
        """Reduce dimensionality of embeddings for visualization."""
        embeddings_array = np.array(embeddings)
        
        if method == "pca":
            reducer = PCA(n_components=n_components)
        elif method == "tsne":
            reducer = TSNE(n_components=n_components, random_state=42)
        else:
            raise ValueError(f"Unsupported dimensionality reduction method: {method}")
        
        reduced_embeddings = reducer.fit_transform(embeddings_array)
        
        logger.info(f"Reduced embeddings from {embeddings_array.shape[1]} to {n_components} dimensions using {method}")
        return reduced_embeddings



