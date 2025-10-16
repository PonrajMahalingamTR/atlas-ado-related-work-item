"""
Configuration management for Semantic Similarity module.
"""

import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class EmbeddingConfig:
    """Configuration for Azure OpenAI embeddings."""
    api_key: str = ""
    endpoint: str = ""
    deployment_name: str = "text-embedding-ada-002"
    api_version: str = "2023-05-15"
    max_tokens: int = 8191
    batch_size: int = 100
    timeout: int = 30

@dataclass
class VectorDBConfig:
    """Configuration for vector database operations."""
    db_type: str = "local"  # "local", "azure_search", "cosmos_db"
    local_db_path: str = "data/vector_db"
    similarity_threshold: float = 0.65  # Lowered threshold for better recall
    max_results: int = 20  # Reduced from 50 for better quality
    embedding_dimension: int = 1536  # text-embedding-ada-002 dimension
    # Dynamic thresholding
    min_similarity_threshold: float = 0.60  # Lowered minimum threshold
    max_similarity_threshold: float = 0.95  # Maximum threshold
    adaptive_threshold: bool = True  # Enable adaptive thresholding

@dataclass
class PreprocessingConfig:
    """Configuration for text preprocessing."""
    remove_html: bool = True
    remove_markdown: bool = True
    remove_code_blocks: bool = True
    remove_urls: bool = True
    remove_emails: bool = True
    normalize_whitespace: bool = True
    max_text_length: int = 8000
    min_text_length: int = 10

@dataclass
class SimilarityConfig:
    """Configuration for similarity calculations."""
    algorithm: str = "cosine"  # "cosine", "euclidean", "dot_product"
    clustering_method: str = "kmeans"  # "kmeans", "dbscan", "hierarchical"
    n_clusters: int = 10
    min_cluster_size: int = 2
    confidence_levels: Dict[str, float] = field(default_factory=lambda: {
        "high": 0.8,
        "medium": 0.6,
        "low": 0.4
    })

@dataclass
class InferenceConfig:
    """Configuration for LLM-based relationship inference."""
    model_name: str = "gpt-4"
    max_tokens: int = 2000
    temperature: float = 0.3
    max_relationships: int = 20
    enable_auto_linking: bool = False
    confidence_threshold: float = 0.8

@dataclass
class SemanticSimilarityConfig:
    """Main configuration class for semantic similarity module."""
    
    # Sub-configurations
    embeddings: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    vector_db: VectorDBConfig = field(default_factory=VectorDBConfig)
    preprocessing: PreprocessingConfig = field(default_factory=PreprocessingConfig)
    similarity: SimilarityConfig = field(default_factory=SimilarityConfig)
    inference: InferenceConfig = field(default_factory=InferenceConfig)
    
    # General settings
    enable_caching: bool = True
    cache_ttl: int = 3600  # 1 hour
    log_level: str = "INFO"
    max_work_items: int = 10000
    
    def __post_init__(self):
        """Initialize configuration from environment variables."""
        self._load_from_env()
        self._validate_config()
    
    def _load_from_env(self):
        """Load configuration from environment variables."""
        # Azure OpenAI settings
        if os.getenv("AZURE_OPENAI_API_KEY"):
            self.embeddings.api_key = os.getenv("AZURE_OPENAI_API_KEY")
        if os.getenv("AZURE_OPENAI_ENDPOINT"):
            self.embeddings.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        if os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"):
            self.embeddings.deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
        
        # Database settings
        if os.getenv("VECTOR_DB_TYPE"):
            self.vector_db.db_type = os.getenv("VECTOR_DB_TYPE")
        if os.getenv("VECTOR_DB_PATH"):
            self.vector_db.local_db_path = os.getenv("VECTOR_DB_PATH")
        
        # Similarity settings
        if os.getenv("SIMILARITY_THRESHOLD"):
            self.vector_db.similarity_threshold = float(os.getenv("SIMILARITY_THRESHOLD"))
    
    def _validate_config(self):
        """Validate configuration values."""
        # Azure OpenAI is optional - will use OpenArena instead
        if not self.embeddings.api_key or self.embeddings.api_key == "your-api-key":
            print("Info: Azure OpenAI API key not configured. Will use OpenArena for embeddings.")
            self.embeddings.api_key = ""
        if not self.embeddings.endpoint or self.embeddings.endpoint == "https://your-resource.openai.azure.com/":
            print("Info: Azure OpenAI endpoint not configured. Will use OpenArena for embeddings.")
            self.embeddings.endpoint = ""
        
        if self.vector_db.similarity_threshold < 0 or self.vector_db.similarity_threshold > 1:
            raise ValueError("Similarity threshold must be between 0 and 1")
        if self.preprocessing.max_text_length < self.preprocessing.min_text_length:
            raise ValueError("Max text length must be greater than min text length")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "embeddings": self.embeddings.__dict__,
            "vector_db": self.vector_db.__dict__,
            "preprocessing": self.preprocessing.__dict__,
            "similarity": self.similarity.__dict__,
            "inference": self.inference.__dict__,
            "enable_caching": self.enable_caching,
            "cache_ttl": self.cache_ttl,
            "log_level": self.log_level,
            "max_work_items": self.max_work_items
        }
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'SemanticSimilarityConfig':
        """Create configuration from dictionary."""
        config = cls()
        
        if "embeddings" in config_dict:
            config.embeddings = EmbeddingConfig(**config_dict["embeddings"])
        if "vector_db" in config_dict:
            config.vector_db = VectorDBConfig(**config_dict["vector_db"])
        if "preprocessing" in config_dict:
            config.preprocessing = PreprocessingConfig(**config_dict["preprocessing"])
        if "similarity" in config_dict:
            config.similarity = SimilarityConfig(**config_dict["similarity"])
        if "inference" in config_dict:
            config.inference = InferenceConfig(**config_dict["inference"])
        
        # General settings
        config.enable_caching = config_dict.get("enable_caching", True)
        config.cache_ttl = config_dict.get("cache_ttl", 3600)
        config.log_level = config_dict.get("log_level", "INFO")
        config.max_work_items = config_dict.get("max_work_items", 10000)
        
        return config
    
    def save_to_file(self, file_path: str):
        """Save configuration to JSON file."""
        import json
        with open(file_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load_from_file(cls, file_path: str) -> 'SemanticSimilarityConfig':
        """Load configuration from JSON file."""
        import json
        with open(file_path, 'r') as f:
            config_dict = json.load(f)
        return cls.from_dict(config_dict)



