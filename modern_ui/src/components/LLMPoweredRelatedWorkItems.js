import React, { useState, useMemo } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  Grid,
  Paper,
  IconButton,
  Tooltip,
  Badge,
  Avatar,
  Button,
  TextField,
  InputAdornment,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Stack,
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  ListItemSecondaryAction,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Alert,
  LinearProgress,
  Collapse,
} from '@mui/material';
import {
  Search as SearchIcon,
  FilterList as FilterListIcon,
  Sort as SortIcon,
  ExpandMore as ExpandMoreIcon,
  Work as WorkIcon,
  Timeline as TimelineIcon,
  Assessment as AssessmentIcon,
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon,
  Info as InfoIcon,
  ArrowForward as ArrowForwardIcon,
  OpenInNew as OpenInNewIcon,
  Star as StarIcon,
  StarBorder as StarBorderIcon,
  Psychology as PsychologyIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
} from '@mui/icons-material';
import { motion, AnimatePresence } from 'framer-motion';

const LLMPoweredRelatedWorkItems = ({ workItems, selectedWorkItem }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [sortBy, setSortBy] = useState('confidenceLevel');
  const [filterByConfidence, setFilterByConfidence] = useState('all');
  const [expandedItems, setExpandedItems] = useState({});
  const [showReasoning, setShowReasoning] = useState({});

  const getConfidenceLevel = (confidence) => {
    // Handle string confidence values from OpenArena analysis
    if (typeof confidence === 'string') {
      return confidence.toLowerCase();
    }
    // Handle numeric confidence values (0.0 to 1.0)
    if (confidence >= 0.8) return 'high';
    if (confidence >= 0.5) return 'medium';
    return 'low';
  };

  const getConfidenceNumericValue = (confidence) => {
    // Convert confidence to numeric value for display
    if (typeof confidence === 'number') {
      return confidence;
    }
    if (typeof confidence === 'string') {
      const level = confidence.toLowerCase();
      if (level === 'high') return 0.9;
      if (level === 'medium') return 0.6;
      if (level === 'low') return 0.3;
    }
    return 0.5; // Default fallback
  };

  const getDynamicAITitle = (confidence) => {
    const confidenceNumeric = getConfidenceNumericValue(confidence);
    
    // High confidence (80%+)
    if (confidenceNumeric >= 0.8) {
      const highConfidenceTitles = [
        '🎯 Strong AI Match:',
        '✨ Perfect AI Discovery:',
        '🚀 High-Confidence Match:',
        '💎 Premium AI Connection:',
        '🔥 AI Power Match:',
        '⭐ Top AI Pick:',
        '🏆 AI Champion:',
        '💪 Strong AI Reasoning:'
      ];
      return highConfidenceTitles[Math.floor(Math.random() * highConfidenceTitles.length)];
    }
    
    // Medium confidence (50-79%)
    else if (confidenceNumeric >= 0.5) {
      const mediumConfidenceTitles = [
        '🔍 AI Connection:',
        '💡 Smart AI Analysis:',
        '🧠 AI Pattern Match:',
        '🔗 AI-Discovered Link:',
        '⚡ AI Insight:',
        '🎪 AI Magic:',
        '🧩 AI Pattern Recognition:',
        '💭 AI Reasoning:'
      ];
      return mediumConfidenceTitles[Math.floor(Math.random() * mediumConfidenceTitles.length)];
    }
    
    // Low confidence (below 50%)
    else {
      const lowConfidenceTitles = [
        '💭 AI Suggestion:',
        '🤔 AI Consideration:',
        '🔍 Potential AI Match:',
        '💡 AI Thought:',
        '🧐 AI Observation:',
        '📝 AI Note:',
        '🤷 AI Maybe:',
        '💫 AI Possibility:'
      ];
      return lowConfidenceTitles[Math.floor(Math.random() * lowConfidenceTitles.length)];
    }
  };

  const filteredAndSortedItems = useMemo(() => {
    if (!workItems || workItems.length === 0) {
      return [];
    }
    
    let filtered = workItems;

    // Filter by search term
    if (searchTerm) {
      filtered = filtered.filter(item =>
        item.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
        item.id.toString().includes(searchTerm) ||
        item.description?.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    // Filter by confidence level
    if (filterByConfidence !== 'all') {
      filtered = filtered.filter(item => {
        const confidence = item.confidence || item.confidenceScore || 0;
        const confidenceLevel = getConfidenceLevel(confidence);
        return confidenceLevel === filterByConfidence;
      });
    }

    // Sort items
    filtered.sort((a, b) => {
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
        case 'confidenceLevel':
        default:
          const confidenceA = a.confidence || a.confidenceScore || 0;
          const confidenceB = b.confidence || b.confidenceScore || 0;
          const levelA = getConfidenceLevel(confidenceA);
          const levelB = getConfidenceLevel(confidenceB);
          const levelOrder = { 'high': 3, 'medium': 2, 'low': 1 };
          return levelOrder[levelB] - levelOrder[levelA];
      }
    });

    return filtered;
  }, [workItems, searchTerm, sortBy, filterByConfidence]);

  const getConfidenceColor = (confidence) => {
    const level = getConfidenceLevel(confidence);
    switch (level) {
      case 'high':
        return '#4caf50'; // Green
      case 'medium':
        return '#ff9800'; // Orange
      case 'low':
        return '#f44336'; // Red
      default:
        return '#757575'; // Grey
    }
  };

  const getConfidenceIcon = (confidence) => {
    const level = getConfidenceLevel(confidence);
    switch (level) {
      case 'high':
        return <CheckCircleIcon />;
      case 'medium':
        return <WarningIcon />;
      case 'low':
        return <InfoIcon />;
      default:
        return <InfoIcon />;
    }
  };

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

  const toggleExpanded = (itemId) => {
    setExpandedItems(prev => ({
      ...prev,
      [itemId]: !prev[itemId]
    }));
  };

  const toggleReasoning = (itemId) => {
    setShowReasoning(prev => ({
      ...prev,
      [itemId]: !prev[itemId]
    }));
  };

  const confidenceStats = useMemo(() => {
    if (!workItems || workItems.length === 0) {
      return { high: 0, medium: 0, low: 0 };
    }
    
    const stats = workItems.reduce((acc, item) => {
      const confidence = item.confidence || item.confidenceScore || 0;
      const level = getConfidenceLevel(confidence);
      acc[level] = (acc[level] || 0) + 1;
      return acc;
    }, {});
    
    // Debug logging
    console.log('LLM Powered Related Work Items - Confidence Stats:', {
      totalItems: workItems.length,
      stats,
      sampleItem: workItems[0] ? {
        id: workItems[0].id,
        confidence: workItems[0].confidence,
        confidenceLevel: workItems[0].confidenceLevel
      } : null
    });
    
    return {
      high: stats.high || 0,
      medium: stats.medium || 0,
      low: stats.low || 0,
    };
  }, [workItems]);

  return (
    <Box sx={{ p: 3 }}>
      {/* Header with Confidence Stats */}
      <Box mb={3}>
        <Typography variant="h5" gutterBottom>
          Related Work Items ({workItems.length})
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          AI-identified work items with relationship confidence scores
        </Typography>
        
        {/* Confidence Score Summary */}
        <Stack direction="row" spacing={2} sx={{ mb: 3 }} flexWrap="wrap">
          <Chip
            icon={<CheckCircleIcon />}
            label={`HIGH: ${confidenceStats.high}`}
            color="success"
            variant="filled"
            size="small"
          />
          <Chip
            icon={<WarningIcon />}
            label={`MEDIUM: ${confidenceStats.medium}`}
            color="warning"
            variant="filled"
            size="small"
          />
          <Chip
            icon={<InfoIcon />}
            label={`LOW: ${confidenceStats.low}`}
            color="error"
            variant="filled"
            size="small"
          />
        </Stack>
      </Box>

      {/* Filters and Search */}
      <Paper elevation={1} sx={{ p: 2, mb: 3 }}>
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
              <InputLabel>Filter by Confidence</InputLabel>
              <Select
                value={filterByConfidence}
                onChange={(e) => setFilterByConfidence(e.target.value)}
                label="Filter by Confidence"
              >
                <MenuItem value="all">All Confidence Levels</MenuItem>
                <MenuItem value="high">High Confidence</MenuItem>
                <MenuItem value="medium">Medium Confidence</MenuItem>
                <MenuItem value="low">Low Confidence</MenuItem>
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
                <MenuItem value="confidenceLevel">Confidence Level</MenuItem>
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
                setFilterByConfidence('all');
                setSortBy('confidenceLevel');
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
          {filteredAndSortedItems.map((item, index) => {
            const confidence = item.confidence || item.confidenceScore || 0;
            const confidenceLevel = getConfidenceLevel(confidence);
            const confidenceNumeric = getConfidenceNumericValue(confidence);
            const confidenceColor = getConfidenceColor(confidence);
            const isExpanded = expandedItems[item.id];
            const isReasoningVisible = showReasoning[item.id];

            return (
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
                    borderLeft: `4px solid ${confidenceColor}`,
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
                          
                          {/* Confidence Score */}
                          <Chip
                            icon={getConfidenceIcon(confidence)}
                            label={`${confidenceLevel.toUpperCase()}`}
                            size="small"
                            sx={{ 
                              backgroundColor: confidenceColor,
                              color: 'white',
                              fontWeight: 'bold',
                            }}
                          />
                          
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

                        {/* AI Reasoning Section */}
                        {(item.reasoning || item.aiReasoning) && (
                          <Box sx={{ mt: 2 }}>
                            <Button
                              variant="text"
                              startIcon={<PsychologyIcon />}
                              onClick={() => toggleReasoning(item.id)}
                              size="small"
                              sx={{ 
                                color: 'primary.main',
                                textTransform: 'none',
                                fontWeight: 'bold',
                              }}
                            >
                              {isReasoningVisible ? 'Hide AI Reasoning' : 'Show AI Reasoning'} →
                            </Button>
                            
                            <Collapse in={isReasoningVisible}>
                              <Paper 
                                elevation={1} 
                                sx={{ 
                                  p: 2, 
                                  mt: 1, 
                                  backgroundColor: 'grey.50',
                                  border: '1px solid',
                                  borderColor: 'grey.200',
                                }}
                              >
                                <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 'bold' }}>
                                  {getDynamicAITitle(item.confidence)}
                                </Typography>
                                <Box
                                  sx={{
                                    whiteSpace: 'pre-line',
                                    wordBreak: 'break-word',
                                    maxWidth: '100%',
                                    overflow: 'visible',
                                    textOverflow: 'unset',
                                    display: 'block',
                                    lineHeight: 1.8,
                                    fontSize: '0.875rem',
                                    color: 'text.secondary',
                                    '& ul': {
                                      margin: 0,
                                      paddingLeft: '1.5rem',
                                      listStyleType: 'disc'
                                    },
                                    '& li': {
                                      marginBottom: '0.5rem'
                                    }
                                  }}
                                  dangerouslySetInnerHTML={{
                                    __html: (item.reasoning || item.aiReasoning || '')
                                      .replace(/\n/g, '<br>')
                                  }}
                                />
                                
                                {/* Confidence Score Details */}
                                <Box sx={{ mt: 2, display: 'flex', alignItems: 'center', gap: 2 }}>
                                  <Typography variant="body2" color="text.secondary">
                                    <strong>Confidence Score:</strong> {(confidenceNumeric * 100).toFixed(1)}%
                                  </Typography>
                                  <LinearProgress 
                                    variant="determinate" 
                                    value={confidenceNumeric * 100} 
                                    sx={{ 
                                      width: 100, 
                                      height: 8, 
                                      borderRadius: 4,
                                      backgroundColor: 'grey.200',
                                      '& .MuiLinearProgress-bar': {
                                        backgroundColor: confidenceColor,
                                      }
                                    }}
                                  />
                                </Box>
                              </Paper>
                            </Collapse>
                          </Box>
                        )}
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
            );
          })}
        </AnimatePresence>

        {filteredAndSortedItems.length === 0 && (
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
  );
};

export default LLMPoweredRelatedWorkItems;
