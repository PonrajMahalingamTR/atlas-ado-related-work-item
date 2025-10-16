import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Button,
  Alert,
  CircularProgress,
  Chip,
  Card,
  CardContent,
  Grid,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Divider
} from '@mui/material';
import {
  Psychology as AIIcon,
  Speed as SpeedIcon,
  Link as LinkIcon,
  ExpandMore as ExpandMoreIcon,
  Group as ClusterIcon,
  Analytics as AnalyticsIcon,
  Insights as InsightsIcon
} from '@mui/icons-material';
import { runSemanticSimilarityAnalysis, runOpenArenaAnalysis } from '../services/api';
import costInfoStore from '../services/costInfoStore';
import { 
  LOADING_MESSAGES, 
  TIMING_CONFIG, 
  calculateProgress, 
  getCurrentPhase, 
  getPhaseProgress,
  createEnhancedRealTimeUpdates
} from '../config/loadingMessages';

const AIDeepDiveWorkflow = ({ 
  workItemId, 
  workItem, 
  onAnalysisComplete, 
  onError,
  selectedModel = 'gemini2pro'
}) => {
  const [workflowStep, setWorkflowStep] = useState('idle'); // 'idle', 'semantic', 'openarena', 'complete'
  const [semanticResults, setSemanticResults] = useState(null);
  const [openArenaResults, setOpenArenaResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [progress, setProgress] = useState(0);
  const [currentStep, setCurrentStep] = useState('');
  const [aiProgress, setAiProgress] = useState({});
  const [expandedClusters, setExpandedClusters] = useState({});
  const [expandedRelationships, setExpandedRelationships] = useState({});

  // Enhanced real-time updates for AI Deep Dive using phase-based timing
  const startRealTimeUpdates = (stepNumber) => {
    const updateCallback = (updateData) => {
      setCurrentStep(updateData.message);
      setProgress(updateData.progress);
      setAiProgress(prev => ({
        ...prev,
        realTimeMessage: updateData.message,
        progress: updateData.progress,
        currentPhase: updateData.currentPhase,
        phaseProgress: updateData.phaseProgress
      }));
    };

    const onComplete = () => {
      // Analysis complete, nothing additional needed here
    };

    const enhancedUpdates = createEnhancedRealTimeUpdates(updateCallback, onComplete);
    enhancedUpdates.start();
    
    return enhancedUpdates;
  };

  const runSemanticAnalysis = async () => {
    if (!workItemId || !workItem) {
      setError('Work item data is required for AI Deep Dive analysis');
      return;
    }

    let enhancedUpdates = null;
    try {
      setLoading(true);
      setError('');
      setWorkflowStep('semantic');
      setProgress(0);
      setCurrentStep('Starting semantic similarity analysis...');

      // Start enhanced real-time updates with phase-based timing
      enhancedUpdates = startRealTimeUpdates(1);
      
      // Wait for phases 1-4 to complete (2 minutes total)
      await new Promise(resolve => setTimeout(resolve, 120000));
      
      // Run semantic similarity analysis during phase 5
      const result = await runSemanticSimilarityAnalysis(workItemId, 'ai_deep_dive');
      
      // Trigger phase 5 completion to show final messages quickly
      if (enhancedUpdates && enhancedUpdates.triggerPhase5Completion) {
        enhancedUpdates.triggerPhase5Completion();
      }
      
      if (result.success) {
        setSemanticResults(result);
        setWorkflowStep('openarena');
        setProgress(100);
        setCurrentStep('Semantic analysis complete! Ready for AI analysis...');
        
        // Extract cost information from semantic analysis if available
        let costInfo = null;
        if (result && result.data && result.data.costInfo) {
          costInfo = result.data.costInfo;
        } else if (result && result.data && result.data.costTracker) {
          costInfo = {
            cost: result.data.costTracker.cost || result.data.costTracker.total_cost || 0.01,
            tokens: result.data.costTracker.tokens || 0,
            model: result.data.costTracker.model || 'semantic-similarity'
          };
        } else if (result && result.costTracker) {
          costInfo = {
            cost: result.costTracker.cost || result.costTracker.total_cost || 0.01,
            tokens: result.costTracker.tokens || 0,
            model: result.costTracker.model || 'semantic-similarity'
          };
        }
        
        // Update cost information via global store (no React re-renders)
        if (costInfo) {
          costInfoStore.setCostInfo(costInfo);
        }
        
        // Auto-proceed to OpenArena analysis
        setTimeout(() => {
          runOpenArenaAnalysis();
        }, 2000);
      } else {
        throw new Error(result.error || 'Semantic similarity analysis failed');
      }
    } catch (err) {
      if (enhancedUpdates && enhancedUpdates.stop) {
        enhancedUpdates.stop();
      }
      setError(`Semantic analysis failed: ${err.message}`);
      setWorkflowStep('idle');
    } finally {
      setLoading(false);
      if (enhancedUpdates && enhancedUpdates.stop) {
        enhancedUpdates.stop();
      }
    }
  };

  const runOpenArenaAnalysis = async () => {
    if (!semanticResults) {
      setError('Semantic analysis results are required for OpenArena analysis');
      return;
    }

    let interval = null;
    try {
      setLoading(true);
      setError('');
      setWorkflowStep('openarena');
      setProgress(0);
      setCurrentStep('Starting OpenArena AI analysis...');

      // Start real-time updates for OpenArena analysis
      interval = startRealTimeUpdates(3);
      
      // Prepare data for OpenArena analysis
      const analysisData = {
        workItem: workItem,
        semanticResults: semanticResults,
        selectedModel: selectedModel
      };

      // Run OpenArena analysis with semantic results
      const result = await runOpenArenaAnalysis(workItemId, analysisData);
      
      clearInterval(interval);
      
      if (result.success) {
        setOpenArenaResults(result);
        setWorkflowStep('complete');
        setProgress(100);
        setCurrentStep('AI Deep Dive analysis complete!');
        
        // Extract cost information if available
        let costInfo = null;
        if (result && result.data && result.data.costInfo) {
          costInfo = result.data.costInfo;
        } else if (result && result.data && result.data.costTracker) {
          costInfo = {
            cost: result.data.costTracker.cost || result.data.costTracker.total_cost || 0.05,
            tokens: result.data.costTracker.tokens || 0,
            model: result.data.costTracker.model || selectedModel || 'unknown'
          };
        } else if (result && result.costTracker) {
          costInfo = {
            cost: result.costTracker.cost || result.costTracker.total_cost || 0.05,
            tokens: result.costTracker.tokens || 0,
            model: result.costTracker.model || selectedModel || 'unknown'
          };
        }
        
        // Update cost information via global store (no React re-renders)
        if (costInfo) {
          costInfoStore.setCostInfo(costInfo);
        }
        
        if (onAnalysisComplete) {
          onAnalysisComplete({
            semanticResults,
            openArenaResults: result,
            workflowType: 'ai_deep_dive'
          });
        }
      } else {
        throw new Error(result.error || 'OpenArena analysis failed');
      }
    } catch (err) {
      if (interval) clearInterval(interval);
      setError(`OpenArena analysis failed: ${err.message}`);
      setWorkflowStep('semantic');
    } finally {
      setLoading(false);
    }
  };

  const handleClusterExpand = (clusterId) => {
    setExpandedClusters(prev => ({
      ...prev,
      [clusterId]: !prev[clusterId]
    }));
  };

  const handleRelationshipExpand = (relationshipId) => {
    setExpandedRelationships(prev => ({
      ...prev,
      [relationshipId]: !prev[relationshipId]
    }));
  };

  const getConfidenceColor = (score) => {
    if (score >= 0.8) return 'success';
    if (score >= 0.6) return 'warning';
    return 'error';
  };

  const getRelationshipIcon = (type) => {
    switch (type) {
      case 'dependency': return <LinkIcon color="primary" />;
      case 'similarity': return <ClusterIcon color="secondary" />;
      case 'hierarchy': return <AnalyticsIcon color="info" />;
      default: return <InsightsIcon color="default" />;
    }
  };

  if (loading) {
    return (
      <Paper sx={{ p: 3, mb: 2 }}>
        <Box sx={{ textAlign: 'center' }}>
          <CircularProgress size={48} sx={{ mb: 2 }} />
          <Typography variant="h6" gutterBottom>
            AI Deep Dive Analysis in Progress
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {currentStep}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {Math.round(progress)}% Complete
          </Typography>
        </Box>
      </Paper>
    );
  }

  if (error) {
    return (
      <Paper sx={{ p: 3, mb: 2 }}>
        <Alert severity="error" sx={{ mb: 2 }}>
          <Typography variant="h6">AI Deep Dive Analysis Error</Typography>
          <Typography variant="body2">{error}</Typography>
        </Alert>
        <Button 
          variant="contained" 
          startIcon={<AIIcon />}
          onClick={runSemanticAnalysis}
          fullWidth
          sx={{
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            color: 'white',
            '&:hover': {
              background: 'linear-gradient(135deg, #5a6fd8 0%, #6a4190 100%)',
            }
          }}
        >
          Retry AI Deep Dive Analysis
        </Button>
      </Paper>
    );
  }

  if (workflowStep === 'idle') {
    return (
      <Paper sx={{ p: 3, mb: 2 }}>
        <Box sx={{ textAlign: 'center' }}>
          <AIIcon sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
          <Typography variant="h6" gutterBottom>
            AI Deep Dive Analysis
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Discover semantically similar work items using AI-powered embeddings, then get intelligent insights from OpenArena.
          </Typography>
          <Button 
            variant="contained" 
            size="large"
            startIcon={<AIIcon />}
            onClick={runSemanticAnalysis}
            sx={{
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              color: 'white',
              minWidth: 200,
              '&:hover': {
                background: 'linear-gradient(135deg, #5a6fd8 0%, #6a4190 100%)',
              }
            }}
          >
            Start AI Deep Dive Analysis
          </Button>
        </Box>
      </Paper>
    );
  }

  return (
    <Box>
      {/* Workflow Status */}
      <Paper sx={{ p: 3, mb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <AIIcon sx={{ fontSize: 32, color: 'primary.main', mr: 2 }} />
          <Box>
            <Typography variant="h6">AI Deep Dive Analysis</Typography>
            <Typography variant="body2" color="text.secondary">
              {workflowStep === 'semantic' && 'Step 1: Semantic Similarity Analysis'}
              {workflowStep === 'openarena' && 'Step 2: OpenArena AI Analysis'}
              {workflowStep === 'complete' && 'Analysis Complete - View Results Below'}
            </Typography>
          </Box>
        </Box>

        <Grid container spacing={2}>
          <Grid item xs={12} md={4}>
            <Card variant="outlined">
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <ClusterIcon sx={{ mr: 1, color: 'primary.main' }} />
                  <Typography variant="h6">Semantic Analysis</Typography>
                </Box>
                <Typography variant="h4" color={semanticResults ? 'primary.main' : 'text.secondary'}>
                  {semanticResults ? '✓' : '○'}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {semanticResults ? 'Complete' : 'Pending'}
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={4}>
            <Card variant="outlined">
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <AIIcon sx={{ mr: 1, color: 'success.main' }} />
                  <Typography variant="h6">AI Analysis</Typography>
                </Box>
                <Typography variant="h4" color={openArenaResults ? 'success.main' : 'text.secondary'}>
                  {openArenaResults ? '✓' : '○'}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {openArenaResults ? 'Complete' : 'Pending'}
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} md={4}>
            <Card variant="outlined">
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <AnalyticsIcon sx={{ mr: 1, color: 'info.main' }} />
                  <Typography variant="h6">Results</Typography>
                </Box>
                <Typography variant="h4" color={workflowStep === 'complete' ? 'info.main' : 'text.secondary'}>
                  {workflowStep === 'complete' ? '✓' : '○'}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {workflowStep === 'complete' ? 'Ready' : 'Pending'}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Paper>

      {/* Semantic Similarity Results */}
      {semanticResults && (
        <Paper sx={{ p: 3, mb: 2 }}>
          <Typography variant="h6" gutterBottom>
            <ClusterIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
            Semantic Similarity Results ({semanticResults.similar_work_items?.length || 0})
          </Typography>
          
          <Grid container spacing={2}>
            {semanticResults.similar_work_items?.slice(0, 6).map((item, index) => (
              <Grid item xs={12} md={6} key={item.id}>
                <Card variant="outlined" sx={{ height: '100%' }}>
                  <CardContent>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                      <Typography variant="h6" noWrap sx={{ flexGrow: 1, mr: 1 }}>
                        #{item.id} - {item.title}
                      </Typography>
                      <Chip 
                        label={`${(item.semanticSimilarityScore * 100).toFixed(1)}%`}
                        color={getConfidenceColor(item.semanticSimilarityScore)}
                        size="small"
                      />
                    </Box>
                    
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                      {item.workItemType} • {item.state}
                    </Typography>
                    
                    <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                      <Chip label={item.areaPath} size="small" variant="outlined" />
                      {item.tags && item.tags.split(';').map((tag, i) => (
                        <Chip key={i} label={tag.trim()} size="small" variant="outlined" />
                      ))}
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </Paper>
      )}

      {/* OpenArena Results */}
      {openArenaResults && (
        <Paper sx={{ p: 3, mb: 2 }}>
          <Typography variant="h6" gutterBottom>
            <AIIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
            AI Analysis Results
          </Typography>
          
          <Box sx={{ mb: 3 }}>
            <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
              {openArenaResults.analysis || 'AI analysis results will appear here...'}
            </Typography>
          </Box>

          {openArenaResults.highConfidenceItems && openArenaResults.highConfidenceItems.length > 0 && (
            <Box sx={{ mb: 3 }}>
              <Typography variant="h6" gutterBottom>
                High Confidence Recommendations ({openArenaResults.highConfidenceItems.length})
              </Typography>
              <Grid container spacing={2}>
                {openArenaResults.highConfidenceItems.slice(0, 3).map((item, index) => (
                  <Grid item xs={12} md={4} key={index}>
                    <Card variant="outlined">
                      <CardContent>
                        <Typography variant="subtitle1" gutterBottom>
                          {item.title}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          {item.description}
                        </Typography>
                      </CardContent>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            </Box>
          )}
        </Paper>
      )}

      {/* Action Buttons */}
      {workflowStep === 'semantic' && (
        <Paper sx={{ p: 3, mb: 2 }}>
          <Box sx={{ textAlign: 'center' }}>
            <Typography variant="h6" gutterBottom>
              Semantic Analysis Complete
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              Ready to proceed with AI analysis using OpenArena
            </Typography>
            <Button 
              variant="contained" 
              size="large"
              startIcon={<AIIcon />}
              onClick={runOpenArenaAnalysis}
              sx={{ 
                minWidth: 200,
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                color: 'white',
                '&:hover': {
                  background: 'linear-gradient(135deg, #5a6fd8 0%, #6a4190 100%)',
                }
              }}
            >
              Continue with AI Analysis
            </Button>
          </Box>
        </Paper>
      )}
    </Box>
  );
};

export default AIDeepDiveWorkflow;
