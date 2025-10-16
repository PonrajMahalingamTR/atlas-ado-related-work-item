# Semantic Similarity Module

This module provides advanced semantic similarity analysis for Azure DevOps work items using Azure OpenAI embeddings and vector similarity search.

## Features

- **Text Preprocessing**: Clean and normalize work item content
- **Azure OpenAI Embeddings**: Generate high-quality embeddings for work items
- **Vector Database**: Efficient similarity search using FAISS
- **Clustering Analysis**: Identify work item clusters and patterns
- **Relationship Inference**: LLM-powered relationship analysis
- **Azure DevOps Integration**: Seamless integration with existing ADO workflows

## Architecture

```
Azure DevOps Work Items
         ↓
    Text Preprocessing
         ↓
   Azure OpenAI Embeddings
         ↓
    Vector Database (FAISS)
         ↓
   Similarity Search
         ↓
   Clustering Analysis
         ↓
   LLM Relationship Inference
         ↓
   ADO Integration Results
```

## Quick Start

### 1. Installation

```bash
# Install dependencies
pip install -r SemanticSimilarity/requirements.txt

# For GPU acceleration (optional)
pip install faiss-gpu
```

### 2. Configuration

Set environment variables:

```bash
export AZURE_OPENAI_API_KEY="your-api-key"
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"
export AZURE_OPENAI_DEPLOYMENT_NAME="text-embedding-ada-002"
```

### 3. Basic Usage

```python
from SemanticSimilarity import SemanticSimilarityConfig, ADOSemanticIntegration

# Create configuration
config = SemanticSimilarityConfig()

# Initialize integration
integration = ADOSemanticIntegration(config, ado_client, openarena_client)

# Analyze work item
result = integration.analyze_work_item_semantic(work_item_id, "ai_deep_dive")

# Get similar work items
similar_items = result.ado_work_items
relationships = result.semantic_analysis.relationships
```

## API Endpoints

### Analyze Work Item
```http
POST /api/semantic-similarity/analyze/{work_item_id}
Content-Type: application/json

{
  "strategy": "ai_deep_dive"
}
```

### Build Vector Database
```http
POST /api/semantic-similarity/build-database
Content-Type: application/json

{
  "limit": 1000
}
```

### Get Database Stats
```http
GET /api/semantic-similarity/database-stats
```

### Health Check
```http
GET /api/semantic-similarity/health
```

## Configuration Options

### Embedding Configuration
- `api_key`: Azure OpenAI API key
- `endpoint`: Azure OpenAI endpoint URL
- `deployment_name`: Embedding model deployment name
- `batch_size`: Number of texts to process in each batch
- `max_tokens`: Maximum tokens per text

### Vector Database Configuration
- `db_type`: Database type ("local" for FAISS)
- `similarity_threshold`: Minimum similarity score (0.0-1.0)
- `max_results`: Maximum number of similar items to return
- `embedding_dimension`: Dimension of embedding vectors

### Preprocessing Configuration
- `remove_html`: Remove HTML tags
- `remove_markdown`: Remove markdown formatting
- `remove_code_blocks`: Remove code blocks
- `max_text_length`: Maximum text length after preprocessing
- `min_text_length`: Minimum text length to process

### Similarity Configuration
- `algorithm`: Similarity algorithm ("cosine", "euclidean", "dot_product")
- `clustering_method`: Clustering method ("kmeans", "dbscan", "hierarchical")
- `n_clusters`: Number of clusters for K-means
- `confidence_levels`: Confidence thresholds for different levels

### Inference Configuration
- `model_name`: LLM model for relationship inference
- `max_relationships`: Maximum number of relationships to infer
- `confidence_threshold`: Minimum confidence for relationships
- `enable_auto_linking`: Enable automatic work item linking

## Integration with AI Deep Dive

The semantic similarity module is designed to enhance the "AI Deep Dive" analysis strategy:

1. **Enhanced Search**: Uses semantic similarity instead of just keyword matching
2. **Relationship Discovery**: Identifies complex relationships between work items
3. **Clustering**: Groups related work items for better organization
4. **Intelligent Linking**: Suggests automatic linking based on confidence scores

## Performance Considerations

- **Batch Processing**: Embeddings are generated in batches for efficiency
- **Caching**: Embeddings are cached to avoid redundant API calls
- **Vector Database**: FAISS provides fast similarity search
- **Async Processing**: Supports asynchronous operations for better performance

## Error Handling

The module includes comprehensive error handling:
- Graceful fallbacks for API failures
- Detailed error messages and logging
- Retry mechanisms for transient failures
- Validation of input data

## Monitoring and Logging

- Detailed logging at all levels
- Performance metrics and timing
- Database statistics and health checks
- Export capabilities for analysis reports

## Future Enhancements

- Azure AI Search integration
- Azure Cosmos DB vector support
- Custom embedding models
- Real-time similarity updates
- Advanced clustering algorithms
- Multi-language support



