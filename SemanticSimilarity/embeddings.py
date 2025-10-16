"""
Azure OpenAI Embeddings Integration

This module handles the generation of embeddings for work items using Azure OpenAI's
embedding models. It provides batching, caching, and error handling capabilities.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
import json
import time
from dataclasses import dataclass
import aiohttp
import numpy as np
from .config import EmbeddingConfig

logger = logging.getLogger(__name__)

@dataclass
class EmbeddingResult:
    """Result of embedding generation."""
    text: str
    embedding: List[float]
    model: str
    usage_tokens: int
    processing_time: float
    success: bool
    error: Optional[str] = None

class AzureOpenAIEmbeddings:
    """Azure OpenAI embeddings client with batching and caching support."""
    
    def __init__(self, config: EmbeddingConfig):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self._cache: Dict[str, EmbeddingResult] = {}
        self._rate_limit_delay = 0.1  # Delay between requests to respect rate limits
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.timeout)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text."""
        import hashlib
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    def _is_cached(self, text: str) -> bool:
        """Check if embedding is cached."""
        cache_key = self._get_cache_key(text)
        return cache_key in self._cache
    
    def _get_cached(self, text: str) -> Optional[EmbeddingResult]:
        """Get cached embedding result."""
        cache_key = self._get_cache_key(text)
        return self._cache.get(cache_key)
    
    def _cache_result(self, result: EmbeddingResult):
        """Cache embedding result."""
        cache_key = self._get_cache_key(result.text)
        self._cache[cache_key] = result
    
    async def _make_request(self, texts: List[str]) -> List[EmbeddingResult]:
        """Make API request to Azure OpenAI embeddings endpoint."""
        if not self.session:
            raise RuntimeError("Client session not initialized. Use async context manager.")
        
        url = f"{self.config.endpoint}/openai/deployments/{self.config.deployment_name}/embeddings"
        url += f"?api-version={self.config.api_version}"
        
        headers = {
            "Content-Type": "application/json",
            "api-key": self.config.api_key
        }
        
        # Prepare input texts
        input_texts = []
        for text in texts:
            # Truncate if too long
            if len(text) > self.config.max_tokens:
                text = text[:self.config.max_tokens]
            input_texts.append(text)
        
        payload = {
            "input": input_texts,
            "model": self.config.deployment_name
        }
        
        try:
            start_time = time.time()
            async with self.session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    processing_time = time.time() - start_time
                    
                    results = []
                    for i, item in enumerate(data.get("data", [])):
                        result = EmbeddingResult(
                            text=input_texts[i],
                            embedding=item.get("embedding", []),
                            model=item.get("model", self.config.deployment_name),
                            usage_tokens=data.get("usage", {}).get("total_tokens", 0),
                            processing_time=processing_time,
                            success=True
                        )
                        results.append(result)
                    
                    logger.info(f"Successfully generated {len(results)} embeddings in {processing_time:.2f}s")
                    return results
                
                else:
                    error_text = await response.text()
                    logger.error(f"API request failed with status {response.status}: {error_text}")
                    return self._create_error_results(texts, f"API error: {response.status}")
        
        except asyncio.TimeoutError:
            logger.error("Embedding request timed out")
            return self._create_error_results(texts, "Request timeout")
        except Exception as e:
            logger.error(f"Embedding request failed: {str(e)}")
            return self._create_error_results(texts, str(e))
    
    def _create_error_results(self, texts: List[str], error: str) -> List[EmbeddingResult]:
        """Create error results for failed requests."""
        return [
            EmbeddingResult(
                text=text,
                embedding=[],
                model=self.config.deployment_name,
                usage_tokens=0,
                processing_time=0,
                success=False,
                error=error
            )
            for text in texts
        ]
    
    async def generate_embeddings(self, texts: List[str]) -> List[EmbeddingResult]:
        """Generate embeddings for a list of texts with batching and caching."""
        if not texts:
            return []
        
        # Check cache first
        cached_results = []
        uncached_texts = []
        uncached_indices = []
        
        for i, text in enumerate(texts):
            if self._is_cached(text):
                cached_results.append((i, self._get_cached(text)))
            else:
                uncached_texts.append(text)
                uncached_indices.append(i)
        
        # Generate embeddings for uncached texts
        all_results = [None] * len(texts)
        
        # Add cached results
        for i, result in cached_results:
            all_results[i] = result
        
        # Process uncached texts in batches
        if uncached_texts:
            batch_size = self.config.batch_size
            for i in range(0, len(uncached_texts), batch_size):
                batch_texts = uncached_texts[i:i + batch_size]
                batch_indices = uncached_indices[i:i + batch_size]
                
                logger.info(f"Processing batch {i//batch_size + 1}: {len(batch_texts)} texts")
                
                # Make API request
                batch_results = await self._make_request(batch_texts)
                
                # Cache successful results
                for result in batch_results:
                    if result.success:
                        self._cache_result(result)
                
                # Add to all results
                for j, result in enumerate(batch_results):
                    all_results[batch_indices[j]] = result
                
                # Rate limiting delay
                if i + batch_size < len(uncached_texts):
                    await asyncio.sleep(self._rate_limit_delay)
        
        return all_results
    
    async def generate_single_embedding(self, text: str) -> EmbeddingResult:
        """Generate embedding for a single text."""
        results = await self.generate_embeddings([text])
        return results[0] if results else EmbeddingResult(
            text=text,
            embedding=[],
            model=self.config.deployment_name,
            usage_tokens=0,
            processing_time=0,
            success=False,
            error="No results returned"
        )
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_cached = len(self._cache)
        successful_cached = sum(1 for r in self._cache.values() if r.success)
        failed_cached = total_cached - successful_cached
        
        return {
            "total_cached": total_cached,
            "successful_cached": successful_cached,
            "failed_cached": failed_cached,
            "cache_hit_rate": len(self._cache) / max(1, len(self._cache))
        }
    
    def clear_cache(self):
        """Clear the embedding cache."""
        self._cache.clear()
        logger.info("Embedding cache cleared")
    
    def save_cache(self, file_path: str):
        """Save cache to file."""
        cache_data = {}
        for key, result in self._cache.items():
            cache_data[key] = {
                "text": result.text,
                "embedding": result.embedding,
                "model": result.model,
                "usage_tokens": result.usage_tokens,
                "processing_time": result.processing_time,
                "success": result.success,
                "error": result.error
            }
        
        with open(file_path, 'w') as f:
            json.dump(cache_data, f, indent=2)
        
        logger.info(f"Cache saved to {file_path}")
    
    def load_cache(self, file_path: str):
        """Load cache from file."""
        try:
            with open(file_path, 'r') as f:
                cache_data = json.load(f)
            
            self._cache = {}
            for key, data in cache_data.items():
                result = EmbeddingResult(
                    text=data["text"],
                    embedding=data["embedding"],
                    model=data["model"],
                    usage_tokens=data["usage_tokens"],
                    processing_time=data["processing_time"],
                    success=data["success"],
                    error=data.get("error")
                )
                self._cache[key] = result
            
            logger.info(f"Cache loaded from {file_path}: {len(self._cache)} items")
        
        except FileNotFoundError:
            logger.warning(f"Cache file {file_path} not found")
        except Exception as e:
            logger.error(f"Failed to load cache from {file_path}: {str(e)}")

# Synchronous wrapper for easier integration
class SyncAzureOpenAIEmbeddings:
    """Synchronous wrapper for Azure OpenAI embeddings."""
    
    def __init__(self, config: EmbeddingConfig):
        self.config = config
        self._async_client = None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        pass
    
    def generate_embeddings(self, texts: List[str]) -> List[EmbeddingResult]:
        """Generate embeddings synchronously."""
        async def _async_generate():
            async with AzureOpenAIEmbeddings(self.config) as client:
                return await client.generate_embeddings(texts)
        
        return asyncio.run(_async_generate())
    
    def generate_single_embedding(self, text: str) -> EmbeddingResult:
        """Generate single embedding synchronously."""
        return self.generate_embeddings([text])[0]



