"""
Semantic Similarity Module for Azure DevOps AI Studio

This module provides semantic similarity analysis capabilities for work items
using Azure OpenAI embeddings and vector similarity search.

Key Components:
- embeddings: Azure OpenAI embeddings integration
- vector_db: Vector database operations and similarity search
- preprocessing: Text preprocessing and normalization
- similarity: Similarity calculation and clustering algorithms
- inference: LLM-based relationship inference
- config: Configuration and settings management
"""

__version__ = "1.0.0"
__author__ = "Azure DevOps AI Studio Team"

from .embeddings import AzureOpenAIEmbeddings
from .vector_db import VectorDatabase
from .preprocessing import TextPreprocessor
from .similarity import SimilarityEngine
from .inference import RelationshipInference
from .config import SemanticSimilarityConfig

__all__ = [
    'AzureOpenAIEmbeddings',
    'VectorDatabase', 
    'TextPreprocessor',
    'SimilarityEngine',
    'RelationshipInference',
    'SemanticSimilarityConfig'
]



