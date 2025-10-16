import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Alert,
  Chip,
  Card,
  CardContent,
  CardActions,
  Grid,
  Divider,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Badge,
  Tooltip,
  LinearProgress,
  TextField,
  InputAdornment,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Stack,
  IconButton,
  Avatar,
} from '@mui/material';
import {
  Psychology as AIIcon,
  Link as LinkIcon,
  Group as ClusterIcon,
  TrendingUp as TrendingUpIcon,
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon,
  Info as InfoIcon,
  ExpandMore as ExpandMoreIcon,
  AutoAwesome as AutoAwesomeIcon,
  Insights as InsightsIcon,
  Speed as SpeedIcon,
  Search as SearchIcon,
  FilterList as FilterListIcon,
  Sort as SortIcon,
  Work as WorkIcon,
  Timeline as TimelineIcon,
  Assessment as AssessmentIcon,
  ArrowForward as ArrowForwardIcon,
  OpenInNew as OpenInNewIcon,
  Star as StarIcon,
  StarBorder as StarBorderIcon,
} from '@mui/icons-material';
import { motion, AnimatePresence } from 'framer-motion';
import costInfoStore from '../services/costInfoStore';
// Progress tracking is now handled by parent component

const SemanticSimilarityAnalysis = ({ 
  workItemId, 
  workItem, 
  onAnalysisComplete,
  onError,
  onAnalysisStart // NEW: Callback when analysis starts
}) => {
  const [analysisData, setAnalysisData] = useState(null);
  const [error, setError] = useState('');
  const [expandedClusters, setExpandedClusters] = useState({});
  const [expandedRelationships, setExpandedRelationships] = useState({});
  const [hasAutoStarted, setHasAutoStarted] = useState(false);
  
  // Filtering state
  const [searchTerm, setSearchTerm] = useState('');
  const [sortBy, setSortBy] = useState('similarity');
  const [filterByType, setFilterByType] = useState('all');

  // Progress tracking is now handled by parent component's SemanticAIProgressBar

  const runSemanticAnalysis = useCallback(async () => {
    if (!workItemId || !workItem) {
      setError('Work item data is required for semantic analysis');
      return;
    }

    try {
      setError('');
      setAnalysisData(null);
      
      // Notify parent component that analysis is starting
      console.log('🔥 SemanticSimilarityAnalysis: About to call onAnalysisStart...');
      console.log('🔥 onAnalysisStart exists:', !!onAnalysisStart);
      if (onAnalysisStart) {
        console.log('🔥 Calling onAnalysisStart() now...');
        onAnalysisStart();
        console.log('🔥 onAnalysisStart() called successfully');
      } else {
        console.warn('❌ onAnalysisStart callback not provided!');
      }

      // Progress tracking is now handled by the parent component's SemanticAIProgressBar
      // No need for local progress tracking here

      // Make API call to semantic similarity endpoint
      const response = await fetch(`/api/semantic-similarity/analyze/${workItemId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          strategy: 'ai_deep_dive'
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      if (!data.success) {
        throw new Error(data.error || 'Semantic analysis failed');
      }

      // Set the analysis data - progress completion is handled by parent
      setAnalysisData(data);

      // Extract cost information if available
      let costInfo = null;
      if (data && data.data && data.data.costInfo) {
        costInfo = data.data.costInfo;
      } else if (data && data.data && data.data.costTracker) {
        costInfo = {
          cost: data.data.costTracker.cost || data.data.costTracker.total_cost || 0.01,
          tokens: data.data.costTracker.tokens || 0,
          model: data.data.costTracker.model || 'semantic-similarity'
        };
      } else if (data && data.costTracker) {
        costInfo = {
          cost: data.costTracker.cost || data.costTracker.total_cost || 0.01,
          tokens: data.costTracker.tokens || 0,
          model: data.costTracker.model || 'semantic-similarity'
        };
      }
      
      // Update cost information via global store (no React re-renders)
      if (costInfo) {
        costInfoStore.setCostInfo(costInfo);
      }

      // Notify parent component
      if (onAnalysisComplete) {
        onAnalysisComplete(data);
      }

    } catch (err) {
      console.error('Semantic analysis error:', err);
      setError(err.message || 'Failed to perform semantic analysis');
      if (onError) {
        onError(err.message);
      }
    } finally {
      // Analysis complete - parent component handles progress completion
    }
  }, [workItemId, workItem, onAnalysisComplete, onError, onAnalysisStart]);

  // Auto-start analysis when component loads or workItemId changes
  useEffect(() => {
    setAnalysisData(null);
    setError('');
    setHasAutoStarted(false);
    
    // Auto-start analysis when component mounts or workItemId changes
    if (workItemId && workItem && !hasAutoStarted) {
      setHasAutoStarted(true);
      // Small delay to ensure component is fully mounted
      setTimeout(() => {
        runSemanticAnalysis();
      }, 100);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workItemId, workItem]); // Intentionally excluding runSemanticAnalysis to prevent infinite loop

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

  const getImpactColor = (level) => {
    switch (level) {
      case 'high': return 'error';
      case 'medium': return 'warning';
      case 'low': return 'info';
      default: return 'default';
    }
  };

  const getRelationshipIcon = (type) => {
    switch (type) {
      case 'dependency': return <LinkIcon />;
      case 'duplicate': return <CheckCircleIcon />;
      case 'related_feature': return <TrendingUpIcon />;
      case 'blocking': return <WarningIcon />;
      case 'technical_debt': return <InfoIcon />;
      default: return <AIIcon />;
    }
  };

  // Loading state is now handled by the parent component's SemanticAIProgressBar
  // No need to show duplicate progress indicators

  // Helper functions for display
  const getStateColor = (state) => {
    const stateColors = {
      'New': '#757575',
      'Active': '#1976d2',
      'Resolved': '#388e3c',
      'Closed': '#2e7d32',
      'Removed': '#d32f2f',
    };
    return stateColors[state] || '#757575';
  };

  const getStateIcon = (state) => {
    const stateIcons = {
      'New': <InfoIcon />,
      'Active': <WorkIcon />,
      'Resolved': <CheckCircleIcon />,
      'Closed': <CheckCircleIcon />,
      'Removed': <WarningIcon />,
    };
    return stateIcons[state] || <InfoIcon />;
  };

  // Convert semantic analysis data to work items format for display
  const workItemsForDisplay = useMemo(() => {
    if (!analysisData?.similar_work_items || analysisData.similar_work_items.length === 0) {
      return [];
    }

    let workItems = analysisData.similar_work_items.map(item => ({
      id: item.id,
      title: item.title,
      type: item.workItemType || 'Unknown',
      state: item.state || 'Unknown',
      priority: item.priority?.toString() || '3',
      assignedTo: item.assignedTo || 'Unassigned',
      createdDate: item.createdDate || new Date().toISOString(),
      areaPath: item.areaPath || 'N/A',
      iterationPath: item.iterationPath || 'N/A',
      tags: item.tags || '',
      description: item.description || '',
      // Add similarity score for display
      similarityScore: item.semanticSimilarityScore || 0
    }));

    // Apply filtering
    if (searchTerm) {
      workItems = workItems.filter(item =>
        item.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
        item.id.toString().includes(searchTerm) ||
        item.description?.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    // Filter by work item type
    if (filterByType !== 'all') {
      workItems = workItems.filter(item => item.type === filterByType);
    }

    // Sort items
    workItems.sort((a, b) => {
      switch (sortBy) {
        case 'title':
          return a.title.localeCompare(b.title);
        case 'state':
          return a.state.localeCompare(b.state);
        case 'type':
          return a.type.localeCompare(b.type);
        case 'assignedTo':
          return (a.assignedTo || 'Unassigned').localeCompare(b.assignedTo || 'Unassigned');
        case 'createdDate':
          return new Date(b.createdDate) - new Date(a.createdDate);
        case 'id':
          return b.id - a.id;
        case 'similarity':
          return b.similarityScore - a.similarityScore;
        default:
          return new Date(b.createdDate) - new Date(a.createdDate);
      }
    });

    return workItems;
  }, [analysisData, searchTerm, sortBy, filterByType]);

  if (error) {
    return (
      <Paper sx={{ p: 3, mb: 2 }}>
        <Alert severity="error" sx={{ mb: 2 }}>
          <Typography variant="h6">Semantic Analysis Error</Typography>
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
          Retry Semantic Analysis
        </Button>
      </Paper>
    );
  }

  if (!analysisData) {
    // Analysis is in progress - parent component shows the SemanticAIProgressBar
    return null; // Don't render anything, let parent handle the progress display
  }

  return (
    <Box>
      {/* Work Items List - Same format as Balanced Search */}
      <Box sx={{ p: 2 }}>
        {/* Filters and Search */}
        <Paper elevation={1} sx={{ p: 2, mb: 2 }}>
          <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} md={4}>
              <TextField
                fullWidth
                placeholder="Search work items..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <SearchIcon />
                    </InputAdornment>
                  ),
                }}
                        size="small"
                      />
            </Grid>
            <Grid item xs={12} md={3}>
              <FormControl fullWidth size="small">
                <InputLabel>Filter by Type</InputLabel>
                <Select
                  value={filterByType}
                  onChange={(e) => setFilterByType(e.target.value)}
                  label="Filter by Type"
                >
                  <MenuItem value="all">All Types</MenuItem>
                  <MenuItem value="User Story">User Story</MenuItem>
                  <MenuItem value="Task">Task</MenuItem>
                  <MenuItem value="Bug">Bug</MenuItem>
                  <MenuItem value="Epic">Epic</MenuItem>
                  <MenuItem value="Feature">Feature</MenuItem>
                  <MenuItem value="Test Case">Test Case</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={3}>
              <FormControl fullWidth size="small">
                <InputLabel>Sort by</InputLabel>
                <Select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value)}
                  label="Sort by"
                >
                  <MenuItem value="similarity">Similarity Score</MenuItem>
                  <MenuItem value="createdDate">Created Date</MenuItem>
                  <MenuItem value="title">Title</MenuItem>
                  <MenuItem value="state">State</MenuItem>
                  <MenuItem value="type">Type</MenuItem>
                  <MenuItem value="assignedTo">Assigned To</MenuItem>
                  <MenuItem value="id">Work Item ID</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} md={2}>
              <Button
                fullWidth
                variant="outlined"
                startIcon={<FilterListIcon />}
                onClick={() => {
                  setSearchTerm('');
                  setFilterByType('all');
                  setSortBy('similarity');
                }}
              >
                Clear Filters
              </Button>
              </Grid>
          </Grid>
        </Paper>

        {/* Work Items List */}
        <Box>
          <AnimatePresence>
            {workItemsForDisplay.map((item, index) => (
              <motion.div
                key={item.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.3, delay: index * 0.05 }}
              >
                <Card 
                  elevation={2} 
                  sx={{ 
                    mb: 2, 
                    borderLeft: `4px solid ${getStateColor(item.state)}`,
                    '&:hover': {
                      elevation: 4,
                      transform: 'translateY(-2px)',
                      transition: 'all 0.2s ease-in-out',
                    }
                  }}
                >
                  <CardContent>
                    <Box display="flex" alignItems="flex-start" justifyContent="space-between">
                      <Box flex={1}>
                        <Box display="flex" alignItems="center" gap={2} mb={1}>
                          <Typography variant="h6" component="div">
                            #{item.id}
                  </Typography>
                    <Chip 
                            label={item.type}
                      size="small" 
                      color="primary" 
                      variant="outlined" 
                    />
                    <Chip 
                            icon={getStateIcon(item.state)}
                            label={item.state}
                      size="small"
                      variant="outlined"
                            sx={{ 
                              borderColor: getStateColor(item.state),
                              color: getStateColor(item.state),
                            }}
                          />
                          {item.priority && (
                    <Chip 
                              label={`Priority: ${item.priority}`}
                      size="small" 
                      variant="outlined" 
                              color={item.priority === '1' ? 'error' : item.priority === '2' ? 'warning' : 'default'}
                    />
                          )}
                          {/* Add similarity score chip */}
                    <Chip 
                            label={`${(item.similarityScore * 100).toFixed(1)}%`}
                      size="small"
                            color={getConfidenceColor(item.similarityScore)}
                            variant="filled"
                          />
                  </Box>
                        
                        <Typography variant="h6" gutterBottom sx={{ mb: 1 }}>
                          {item.title}
          </Typography>
          
                        <Grid container spacing={1} sx={{ mt: 1 }}>
                          <Grid item xs={12} sm={6}>
                            <Typography variant="body2" color="text.secondary">
                              <strong>Assigned to:</strong> {item.assignedTo || 'Unassigned'}
                            </Typography>
                          </Grid>
                          <Grid item xs={12} sm={6}>
                            <Typography variant="body2" color="text.secondary">
                              <strong>Created:</strong> {item.createdDate ? new Date(item.createdDate).toLocaleDateString() : 'N/A'}
                            </Typography>
                          </Grid>
                          <Grid item xs={12}>
                            <Typography variant="body2" color="text.secondary">
                              <strong>Area:</strong> {item.areaPath || 'N/A'}
                            </Typography>
                          </Grid>
                          <Grid item xs={12}>
                            <Typography variant="body2" color="text.secondary">
                              <strong>Iteration:</strong> {item.iterationPath || 'N/A'}
                  </Typography>
                          </Grid>
                          {item.tags && (
                            <Grid item xs={12}>
                              <Typography variant="body2" color="text.secondary">
                                <strong>Tags:</strong> {item.tags}
                  </Typography>
                            </Grid>
                          )}
            </Grid>
            
                      </Box>

                      <Box display="flex" flexDirection="column" gap={1}>
                        <Tooltip title="View in Azure DevOps">
                          <IconButton 
                            size="small"
                            onClick={() => window.open(`https://dev.azure.com/your-organization/your-project/_workitems/edit/${item.id}`, '_blank')}
                          >
                            <OpenInNewIcon />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Add to Favorites">
                          <IconButton size="small">
                            <StarBorderIcon />
                          </IconButton>
                        </Tooltip>
                      </Box>
                    </Box>
                </CardContent>
              </Card>
              </motion.div>
            ))}
          </AnimatePresence>

          {workItemsForDisplay.length === 0 && (
            <Paper elevation={1} sx={{ p: 4, textAlign: 'center' }}>
              <Typography variant="h6" color="text.secondary" gutterBottom>
                No work items found
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Try adjusting your search criteria or filters
              </Typography>
        </Paper>
      )}
        </Box>
      </Box>

      {/* Action Buttons */}
      <Paper sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center' }}>
          <Button 
            variant="contained" 
            startIcon={<AIIcon />}
            onClick={runSemanticAnalysis}
            sx={{
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              color: 'white',
              '&:hover': {
                background: 'linear-gradient(135deg, #5a6fd8 0%, #6a4190 100%)',
              }
            }}
          >
            Re-run Analysis
          </Button>
          <Button 
            variant="outlined" 
            startIcon={<InsightsIcon />}
            onClick={() => {
              // Export analysis data
              const dataStr = JSON.stringify(analysisData, null, 2);
              const dataBlob = new Blob([dataStr], { type: 'application/json' });
              const url = URL.createObjectURL(dataBlob);
              const link = document.createElement('a');
              link.href = url;
              link.download = `semantic_analysis_${workItemId}_${new Date().toISOString().split('T')[0]}.json`;
              link.click();
            }}
          >
            Export Analysis
          </Button>
        </Box>
      </Paper>
    </Box>
  );
};

export default SemanticSimilarityAnalysis;



