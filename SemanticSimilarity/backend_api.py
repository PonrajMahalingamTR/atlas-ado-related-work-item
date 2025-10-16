"""
Backend API Integration for Semantic Similarity

This module provides Flask API endpoints for semantic similarity analysis
that integrate with the existing Azure DevOps AI Studio backend.
"""

import logging
from typing import Dict, Any, Optional
from flask import Blueprint, request, jsonify, current_app
import traceback
from datetime import datetime

from .ado_integration import ADOSemanticIntegration
from .enhanced_ado_integration import EnhancedADOSemanticIntegration
from .config import SemanticSimilarityConfig

logger = logging.getLogger(__name__)

# Create Blueprint for semantic similarity API
semantic_similarity_bp = Blueprint('semantic_similarity', __name__, url_prefix='/api/semantic-similarity')

def get_semantic_integration() -> Optional[ADOSemanticIntegration]:
    """Get semantic integration instance from app context."""
    return getattr(current_app, 'semantic_integration', None)

@semantic_similarity_bp.route('/analyze/<int:work_item_id>', methods=['POST'])
def analyze_work_item_semantic(work_item_id):
    """Analyze work item using semantic similarity (AI Deep Dive)."""
    try:
        # Get request data
        data = request.get_json() or {}
        analysis_strategy = data.get('strategy', 'ai_deep_dive')
        use_enhanced = data.get('use_enhanced', True)  # Default to enhanced approach
        
        # Get ADO client and OpenArena client from app context
        ado_client = current_app.config.get('ado_client')
        openarena_client = current_app.config.get('openarena_client')
        
        if not ado_client or not openarena_client:
            return jsonify({
                'error': 'ADO client or OpenArena client not available',
                'success': False
            }), 500
        
        # Create appropriate integration instance
        config = SemanticSimilarityConfig()
        
        if use_enhanced:
            # Use enhanced approach with automatic ADO calls and system prompt
            logger.info(f"Using enhanced semantic analysis approach for work item {work_item_id}")
            integration = EnhancedADOSemanticIntegration(config, ado_client, openarena_client)
            result = integration.analyze_work_item_semantic_enhanced(work_item_id, analysis_strategy)
        else:
            # Use original approach
            logger.info(f"Using original semantic analysis approach for work item {work_item_id}")
            semantic_integration = get_semantic_integration()
            if not semantic_integration:
                return jsonify({
                    'error': 'Semantic similarity integration not available',
                    'success': False
                }), 500
            result = semantic_integration.analyze_work_item_semantic(work_item_id, analysis_strategy)
        
        logger.info(f"Semantic analysis result: success={result.success}, error={result.error}")
        
        if not result.success:
            logger.error(f"Semantic analysis failed: {result.error}")
            return jsonify({
                'error': result.error,
                'success': False
            }), 500
        
        # Extract cost information from analysis metadata
        cost_info = None
        try:
            if (result.semantic_analysis and 
                hasattr(result.semantic_analysis, 'analysis_metadata') and
                result.semantic_analysis.analysis_metadata and 
                'embedding' in result.semantic_analysis.analysis_metadata):
                
                embedding_metadata = result.semantic_analysis.analysis_metadata['embedding']
                if 'usage_tokens' in embedding_metadata and 'model' in embedding_metadata:
                    # Calculate estimated cost based on tokens and model
                    tokens = embedding_metadata['usage_tokens']
                    model = embedding_metadata['model']
                    
                    # Rough cost estimates per 1000 tokens (these should be updated with actual pricing)
                    cost_per_1k_tokens = {
                        'text-embedding-ada-002': 0.0001,  # $0.0001 per 1K tokens
                        'text-embedding-3-small': 0.00002,  # $0.00002 per 1K tokens
                        'text-embedding-3-large': 0.00013,  # $0.00013 per 1K tokens
                        'default': 0.0001
                    }
                    
                    cost_per_token = cost_per_1k_tokens.get(model, cost_per_1k_tokens['default']) / 1000
                    estimated_cost = tokens * cost_per_token
                    
                    cost_info = {
                        'cost': round(estimated_cost, 6),
                        'tokens': tokens,
                        'model': model,
                        'timestamp': datetime.now().isoformat()
                    }
                    logger.info(f"Semantic analysis cost info extracted: cost=${cost_info['cost']:.6f}, tokens={cost_info['tokens']}, model={cost_info['model']}")
                else:
                    logger.warning("Embedding metadata missing usage_tokens or model information")
            else:
                logger.warning("Semantic analysis metadata not available for cost calculation")
        except Exception as cost_error:
            logger.warning(f"Failed to extract cost information: {cost_error}")
            # Continue without cost info rather than failing the entire request
        
        # Prepare response
        response_data = {
            'success': True,
            'work_item_id': result.work_item_id,
            'similar_work_items': result.ado_work_items,
            'analysis_metadata': result.integration_metadata,
            'enhanced_approach': use_enhanced,
            'relationship_insights': integration.get_relationship_insights(result) if hasattr(integration, 'get_relationship_insights') else {},
            'costInfo': cost_info,
            'semantic_analysis': {
                'clusters': [
                    {
                        'cluster_id': cluster.cluster_id,
                        'size': cluster.size,
                        'avg_similarity': cluster.avg_similarity,
                        'dominant_work_item_type': cluster.dominant_work_item_type,
                        'common_tags': cluster.common_tags
                    }
                    for cluster in result.semantic_analysis.clusters
                ],
                'relationships': [
                    {
                        'work_item_1_id': rel.work_item_1_id,
                        'work_item_2_id': rel.work_item_2_id,
                        'relationship_type': rel.relationship_type,
                        'confidence_score': rel.confidence_score,
                        'explanation': rel.explanation,
                        'evidence': rel.evidence,
                        'suggested_action': rel.suggested_action,
                        'impact_level': rel.impact_level,
                        'is_automatic_linkable': rel.is_automatic_linkable
                    }
                    for rel in result.semantic_analysis.relationships
                ]
            }
        }
        
        logger.info(f"Semantic analysis completed for work item {work_item_id}")
        return jsonify(response_data)
    
    except Exception as e:
        logger.error(f"Semantic analysis API error: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Provide more specific error messages based on the error type
        error_message = str(e)
        if "ADO client not available" in error_message:
            error_message = "Azure DevOps connection not available. Please check your connection settings."
        elif "not found" in error_message:
            error_message = f"Work item {work_item_id} not found in Azure DevOps."
        elif "analysis_metadata" in error_message:
            error_message = "Semantic analysis metadata error. Please try again."
        
        return jsonify({
            'error': f'Semantic analysis failed: {error_message}',
            'success': False
        }), 500

@semantic_similarity_bp.route('/build-database', methods=['POST'])
def build_vector_database():
    """Build vector database from work items."""
    try:
        # Get request data
        data = request.get_json() or {}
        work_item_limit = data.get('limit', 1000)
        
        # Get semantic integration
        semantic_integration = get_semantic_integration()
        if not semantic_integration:
            return jsonify({
                'error': 'Semantic similarity integration not available',
                'success': False
            }), 500
        
        # Get work items from ADO
        ado_client = semantic_integration.ado_client
        if not ado_client:
            return jsonify({
                'error': 'ADO client not available',
                'success': False
            }), 500
        
        work_items = ado_client.get_work_items(limit=work_item_limit)
        
        # Clear the vector database first to ensure fresh embeddings
        logger.info("Clearing vector database before building new database")
        semantic_integration.semantic_engine.vector_db.clear_database()
        
        # Build vector database
        success = semantic_integration.semantic_engine.build_vector_database(work_items)
        
        if success:
            # Get database stats
            stats = semantic_integration.semantic_engine.get_database_stats()
            
            return jsonify({
                'success': True,
                'message': f'Vector database built with {len(work_items)} work items',
                'database_stats': stats
            })
        else:
            return jsonify({
                'error': 'Failed to build vector database',
                'success': False
            }), 500
    
    except Exception as e:
        logger.error(f"Build database API error: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'error': f'Failed to build database: {str(e)}',
            'success': False
        }), 500

@semantic_similarity_bp.route('/database-stats', methods=['GET'])
def get_database_stats():
    """Get vector database statistics."""
    try:
        semantic_integration = get_semantic_integration()
        if not semantic_integration:
            return jsonify({
                'error': 'Semantic similarity integration not available',
                'success': False
            }), 500
        
        stats = semantic_integration.semantic_engine.get_database_stats()
        
        return jsonify({
            'success': True,
            'database_stats': stats
        })
    
    except Exception as e:
        logger.error(f"Database stats API error: {str(e)}")
        return jsonify({
            'error': f'Failed to get database stats: {str(e)}',
            'success': False
        }), 500

@semantic_similarity_bp.route('/clear-database', methods=['POST'])
def clear_database():
    """Clear vector database."""
    try:
        semantic_integration = get_semantic_integration()
        if not semantic_integration:
            return jsonify({
                'error': 'Semantic similarity integration not available',
                'success': False
            }), 500
        
        semantic_integration.semantic_engine.clear_database()
        
        return jsonify({
            'success': True,
            'message': 'Vector database cleared'
        })
    
    except Exception as e:
        logger.error(f"Clear database API error: {str(e)}")
        return jsonify({
            'error': f'Failed to clear database: {str(e)}',
            'success': False
        }), 500

@semantic_similarity_bp.route('/export-analysis/<int:work_item_id>', methods=['GET'])
def export_analysis_report(work_item_id):
    """Export analysis report for a work item."""
    try:
        # Get request parameters
        analysis_strategy = request.args.get('strategy', 'ai_deep_dive')
        
        semantic_integration = get_semantic_integration()
        if not semantic_integration:
            return jsonify({
                'error': 'Semantic similarity integration not available',
                'success': False
            }), 500
        
        # Perform analysis
        result = semantic_integration.analyze_work_item_semantic(work_item_id, analysis_strategy)
        
        if not result.success:
            return jsonify({
                'error': result.error,
                'success': False
            }), 500
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'semantic_analysis_{work_item_id}_{timestamp}.json'
        
        # Export report
        success = semantic_integration.export_analysis_report(result, filename)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Analysis report exported to {filename}',
                'filename': filename
            })
        else:
            return jsonify({
                'error': 'Failed to export analysis report',
                'success': False
            }), 500
    
    except Exception as e:
        logger.error(f"Export analysis API error: {str(e)}")
        return jsonify({
            'error': f'Failed to export analysis: {str(e)}',
            'success': False
        }), 500

@semantic_similarity_bp.route('/health', methods=['GET'])
def health_check():
    """Health check for semantic similarity service."""
    try:
        semantic_integration = get_semantic_integration()
        if not semantic_integration:
            return jsonify({
                'status': 'unhealthy',
                'message': 'Semantic similarity integration not available'
            }), 500
        
        # Check if database is populated
        stats = semantic_integration.semantic_engine.get_database_stats()
        is_healthy = stats['vector_database']['total_vectors'] > 0
        
        return jsonify({
            'status': 'healthy' if is_healthy else 'degraded',
            'message': 'Semantic similarity service is running',
            'database_vectors': stats['vector_database']['total_vectors'],
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'message': f'Semantic similarity service error: {str(e)}'
        }), 500

def register_semantic_similarity_routes(app, ado_client=None, openarena_client=None):
    """Register semantic similarity routes with Flask app."""
    try:
        # Create semantic similarity configuration
        config = SemanticSimilarityConfig()
        
        # Create semantic integration
        semantic_integration = ADOSemanticIntegration(config, ado_client, openarena_client)
        
        # Store in app context
        app.semantic_integration = semantic_integration
        
        # Register blueprint
        app.register_blueprint(semantic_similarity_bp)
        
        logger.info("Semantic similarity routes registered successfully")
        return True
    
    except ValueError as e:
        if "Azure OpenAI API key is required" in str(e):
            logger.warning("Semantic similarity routes registered but Azure OpenAI API key not configured")
            # Still register the blueprint but with limited functionality
            app.register_blueprint(semantic_similarity_bp)
            return True
        else:
            logger.error(f"Configuration validation failed: {str(e)}")
            return False
    except Exception as e:
        logger.error(f"Failed to register semantic similarity routes: {str(e)}")
        return False
