import React, { useState, useMemo } from 'react';
import {
  Box,
  Typography,
  Paper,
  Card,
  CardContent,
  Chip,
  Collapse,
  IconButton,
  LinearProgress,
  Tooltip,
  Divider,
} from '@mui/material';
import {
  CheckCircle as CheckCircleIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Star as StarIcon,
  Share as ShareIcon,
} from '@mui/icons-material';
import { motion, AnimatePresence } from 'framer-motion';

const PowerMatchesSection = ({ workItems = [] }) => {
  const [expandedItems, setExpandedItems] = useState({});

  const getConfidenceLevel = (confidence) => {
    if (confidence >= 0.8) return 'high';
    if (confidence >= 0.5) return 'medium';
    return 'low';
  };

  const getConfidenceNumericValue = (confidence) => {
    if (typeof confidence === 'number') return confidence;
    if (typeof confidence === 'string') {
      const level = confidence.toLowerCase();
      if (level === 'high') return 0.9;
      if (level === 'medium') return 0.6;
      if (level === 'low') return 0.3;
    }
    return 0.5;
  };

  const getConfidenceColor = (confidence) => {
    const level = getConfidenceLevel(confidence);
    switch (level) {
      case 'high':
        return '#4caf50';
      case 'medium':
        return '#ff9800';
      case 'low':
        return '#f44336';
      default:
        return '#757575';
    }
  };

  const getStateColor = (state) => {
    const stateLower = state?.toLowerCase() || '';
    if (stateLower.includes('new')) return '#2196f3';
    if (stateLower.includes('active')) return '#4caf50';
    if (stateLower.includes('closed')) return '#9e9e9e';
    if (stateLower.includes('resolved')) return '#4caf50';
    return '#757575';
  };

  const getDynamicAITitle = (confidence) => {
    const confidenceNumeric = getConfidenceNumericValue(confidence);
    if (confidenceNumeric >= 0.9) return '🎯 AI Champion:';
    if (confidenceNumeric >= 0.8) return '⭐ Premium AI Match:';
    if (confidenceNumeric >= 0.7) return '💎 Strong AI Connection:';
    if (confidenceNumeric >= 0.6) return '🔍 AI Discovery:';
    return '💭 AI Suggestion:';
  };

  const highConfidenceItems = useMemo(() => {
    return (workItems || [])
      .filter(item => {
        const confidence = item.confidence || item.confidenceScore || 0;
        return confidence >= 0.8;
      })
      .slice(0, 3); // Show up to 3 high confidence items (or all if less than 3)
  }, [workItems]);

  const toggleReasoning = (itemId) => {
    setExpandedItems(prev => ({
      ...prev,
      [itemId]: !prev[itemId]
    }));
  };

  if (highConfidenceItems.length === 0) {
    return (
      <Box sx={{ p: 3, textAlign: 'center' }}>
        <Typography variant="body1" color="text.secondary">
          No high confidence AI matches found
        </Typography>
      </Box>
    );
  }

  const itemCount = highConfidenceItems.length;
  const countText = itemCount === 1 ? 'Top 1' : `Top ${itemCount}`;

  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        {countText} AI-identified work items with the strongest relationships to your selected item
      </Typography>
      
      <AnimatePresence>
        {highConfidenceItems.map((item, index) => {
          const confidence = item.confidence || item.confidenceScore || 0;
          const confidenceNumeric = getConfidenceNumericValue(confidence);
          const confidenceColor = getConfidenceColor(confidence);
          const stateColor = getStateColor(item.state);
          const isReasoningVisible = expandedItems[item.id] || false;

          return (
            <motion.div
              key={item.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3, delay: index * 0.1 }}
            >
              <Card
                sx={{
                  mb: 2,
                  border: '1px solid',
                  borderColor: 'grey.200',
                  borderRadius: 2,
                  boxShadow: 1,
                  '&:hover': {
                    boxShadow: 3,
                    borderColor: 'primary.light',
                  },
                }}
              >
                <CardContent sx={{ p: 2 }}>
                  {/* Header with ID, Status, and Actions */}
                  <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
                    <Box display="flex" alignItems="center" gap={1}>
                      <CheckCircleIcon sx={{ color: confidenceColor, fontSize: 20 }} />
                      <Typography variant="h6" sx={{ fontWeight: 'bold', color: 'text.primary' }}>
                        #{item.id}
                      </Typography>
                      <Chip
                        label={item.state || 'Unknown'}
                        size="small"
                        sx={{
                          backgroundColor: stateColor,
                          color: 'white',
                          fontWeight: 'bold',
                          fontSize: '0.75rem',
                        }}
                      />
                      <Chip
                        label="HIGH"
                        size="small"
                        sx={{
                          backgroundColor: '#4caf50',
                          color: 'white',
                          fontWeight: 'bold',
                          fontSize: '0.75rem',
                        }}
                      />
                      <Chip
                        label={item.type || 'Unknown'}
                        size="small"
                        variant="outlined"
                        sx={{
                          borderColor: '#2196f3',
                          color: '#2196f3',
                          fontWeight: 'bold',
                          fontSize: '0.75rem',
                        }}
                      />
                    </Box>
                    
                    <Box display="flex" alignItems="center" gap={1}>
                      <Typography variant="caption" color="text.secondary" sx={{ mr: 1 }}>
                        Priority: {item.priority || 'N/A'}
                      </Typography>
                      <Tooltip title="Share">
                        <IconButton size="small">
                          <ShareIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Favorite">
                        <IconButton size="small">
                          <StarIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </Box>
                  </Box>

                  {/* Title */}
                  <Typography variant="h6" sx={{ mb: 2, fontWeight: 'medium', lineHeight: 1.4 }}>
                    {item.title || 'No Title'}
                  </Typography>

                  {/* Metadata */}
                  <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
                    <Typography variant="body2" color="text.secondary">
                      Assigned to: {item.assignedTo || 'Unassigned'}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Created: {item.createdDate || 'N/A'}
                    </Typography>
                  </Box>

                  <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
                    <Typography variant="body2" color="text.secondary">
                      Area: {item.areaPath || 'N/A'}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Iteration: {item.iterationPath || 'N/A'}
                    </Typography>
                  </Box>

                  {/* AI Reasoning Toggle */}
                  <Box sx={{ mt: 2 }}>
                    <Box
                      onClick={() => toggleReasoning(item.id)}
                      sx={{
                        display: 'flex',
                        alignItems: 'center',
                        cursor: 'pointer',
                        color: 'primary.main',
                        '&:hover': { textDecoration: 'underline' }
                      }}
                    >
                      <CheckCircleIcon sx={{ fontSize: 16, mr: 1 }} />
                      <Typography variant="body2" sx={{ fontWeight: 'medium' }}>
                        {isReasoningVisible ? 'Hide AI Reasoning' : 'Show AI Reasoning'} →
                      </Typography>
                    </Box>

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
                        
                        {/* Confidence Score */}
                        <Box sx={{ mt: 2 }}>
                          <Box display="flex" alignItems="center" justifyContent="space-between" mb={1}>
                            <Typography variant="caption" color="text.secondary">
                              Confidence Score: {(confidenceNumeric * 100).toFixed(1)}%
                            </Typography>
                          </Box>
                          <LinearProgress
                            variant="determinate"
                            value={confidenceNumeric * 100}
                            sx={{
                              height: 6,
                              borderRadius: 3,
                              backgroundColor: 'grey.200',
                              '& .MuiLinearProgress-bar': {
                                backgroundColor: confidenceColor,
                                borderRadius: 3,
                              },
                            }}
                          />
                        </Box>
                      </Paper>
                    </Collapse>
                  </Box>
                </CardContent>
              </Card>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </Box>
  );
};

export default PowerMatchesSection;
