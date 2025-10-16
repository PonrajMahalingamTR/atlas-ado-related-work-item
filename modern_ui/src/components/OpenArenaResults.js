import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  CircularProgress,
  Alert,
  Card,
  CardContent,
  Chip,
  Divider,
  IconButton,
  Tooltip,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
} from '@mui/material';
import {
  Psychology as AIIcon,
  Launch as LaunchIcon,
  CheckCircle as CheckCircleIcon,
  Warning as WarningIcon,
  Info as InfoIcon,
  ExpandMore as ExpandMoreIcon,
  ContentCopy as CopyIcon,
  Download as DownloadIcon,
  Share as ShareIcon,
} from '@mui/icons-material';
import { getModelDisplayName } from './ModelIcon';

const OpenArenaResults = ({ 
  workItem, 
  relatedWorkItems, 
  openArenaResults, 
  loading, 
  onLaunchModernUI 
}) => {
  const [expandedSection, setExpandedSection] = useState('analysis');

  const handleSectionChange = (panel) => (event, isExpanded) => {
    setExpandedSection(isExpanded ? panel : false);
  };

  const handleCopyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
  };

  const handleExportToFile = () => {
    if (!openArenaResults) return;
    
    const dataStr = JSON.stringify(openArenaResults, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
    
    const exportFileDefaultName = `openarena-analysis-${workItem?.id || 'unknown'}.json`;
    
    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();
  };

  if (loading) {
    return (
      <Paper sx={{ p: 4, textAlign: 'center' }}>
        <CircularProgress size={40} sx={{ mb: 2 }} />
        <Typography variant="h6" gutterBottom>
          🤖 OpenArena AI Analysis in Progress...
        </Typography>
        <Typography variant="body2" color="text.secondary">
          This may take up to 60 seconds depending on the complexity of the analysis.
        </Typography>
      </Paper>
    );
  }

  if (!openArenaResults) {
    return (
      <Paper sx={{ p: 4, textAlign: 'center' }}>
        <AIIcon sx={{ fontSize: 64, color: 'primary.main', mb: 2 }} />
        <Typography variant="h5" gutterBottom>
          OpenArena AI Analysis
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
          Click "Analysis with AI Model" to run OpenArena websocket analysis on your work items.
        </Typography>
        <Typography variant="body2" color="text.secondary">
          This will analyze the selected work item and all related work items using advanced AI models.
        </Typography>
      </Paper>
    );
  }

  const { 
    analysisResults, 
    costInfo, 
    modelUsed, 
    timestamp,
    highConfidenceItems = [],
    mediumConfidenceItems = [],
    lowConfidenceItems = [],
    relationshipPatterns = [],
    riskAssessment = [],
    recommendations = []
  } = openArenaResults;

  const totalItems = highConfidenceItems.length + mediumConfidenceItems.length + lowConfidenceItems.length;

  return (
    <Box>
      {/* Header Section */}
      <Paper sx={{ p: 3, mb: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Box>
            <Typography variant="h5" gutterBottom>
              🤖 OpenArena AI Analysis Results
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Analysis completed using {getModelDisplayName(modelUsed)} • {timestamp ? new Date(timestamp).toLocaleString() : 'Recently'}
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button
              variant="outlined"
              startIcon={<CopyIcon />}
              onClick={() => handleCopyToClipboard(JSON.stringify(openArenaResults, null, 2))}
              size="small"
            >
              Copy
            </Button>
            <Button
              variant="outlined"
              startIcon={<DownloadIcon />}
              onClick={handleExportToFile}
              size="small"
            >
              Export
            </Button>
            <Button
              variant="contained"
              startIcon={<LaunchIcon />}
              onClick={onLaunchModernUI}
              size="small"
              sx={{
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                color: 'white',
                '&:hover': {
                  background: 'linear-gradient(135deg, #5a6fd8 0%, #6a4190 100%)',
                }
              }}
            >
              Launch Modern UI
            </Button>
          </Box>
        </Box>

        {/* Cost Information */}
        {costInfo && (
          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
            <Chip 
              icon={<InfoIcon />} 
              label={`Cost: $${(costInfo.cost || 0).toFixed(3)}`} 
              color="primary" 
              variant="outlined" 
            />
            <Chip 
              icon={<AIIcon />} 
              label={`Tokens: ${costInfo.tokens || '0'}`} 
              color="secondary" 
              variant="outlined" 
            />
            <Chip 
              icon={<CheckCircleIcon />} 
              label={`Items Analyzed: ${totalItems}`} 
              color="success" 
              variant="outlined" 
            />
          </Box>
        )}
      </Paper>

      {/* Analysis Results */}
      <Accordion 
        expanded={expandedSection === 'analysis'} 
        onChange={handleSectionChange('analysis')}
      >
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography variant="h6">
            📊 Analysis Results ({totalItems} items found)
          </Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
            <Chip 
              icon={<CheckCircleIcon />} 
              label={`High: ${highConfidenceItems.length}`} 
              color="success" 
              size="small"
            />
            <Chip 
              icon={<WarningIcon />} 
              label={`Medium: ${mediumConfidenceItems.length}`} 
              color="warning" 
              size="small"
            />
            <Chip 
              icon={<InfoIcon />} 
              label={`Low: ${lowConfidenceItems.length}`} 
              color="info" 
              size="small"
            />
          </Box>

          {/* High Confidence Items */}
          {highConfidenceItems.length > 0 && (
            <Box sx={{ mb: 3 }}>
              <Typography variant="h6" color="success.main" gutterBottom>
                High Confidence Relationships
              </Typography>
              <List>
                {highConfidenceItems.map((item, index) => (
                  <ListItem key={index} sx={{ border: 1, borderColor: 'success.light', borderRadius: 1, mb: 1 }}>
                    <ListItemIcon>
                      <CheckCircleIcon color="success" />
                    </ListItemIcon>
                    <ListItemText
                      primary={`#${item.id} - ${item.title}`}
                      secondary={
                        <Box>
                          <Typography variant="body2" color="text.secondary">
                            {item.relationshipType} • {item.confidence}
                          </Typography>
                          <Typography variant="body2">
                            {item.reasoning || item.evidence}
                          </Typography>
                        </Box>
                      }
                    />
                  </ListItem>
                ))}
              </List>
            </Box>
          )}

          {/* Medium Confidence Items */}
          {mediumConfidenceItems.length > 0 && (
            <Box sx={{ mb: 3 }}>
              <Typography variant="h6" color="warning.main" gutterBottom>
                Medium Confidence Relationships
              </Typography>
              <List>
                {mediumConfidenceItems.map((item, index) => (
                  <ListItem key={index} sx={{ border: 1, borderColor: 'warning.light', borderRadius: 1, mb: 1 }}>
                    <ListItemIcon>
                      <WarningIcon color="warning" />
                    </ListItemIcon>
                    <ListItemText
                      primary={`#${item.id} - ${item.title}`}
                      secondary={
                        <Box>
                          <Typography variant="body2" color="text.secondary">
                            {item.relationshipType} • {item.confidence}
                          </Typography>
                          <Typography variant="body2">
                            {item.reasoning || item.evidence}
                          </Typography>
                        </Box>
                      }
                    />
                  </ListItem>
                ))}
              </List>
            </Box>
          )}

          {/* Low Confidence Items */}
          {lowConfidenceItems.length > 0 && (
            <Box sx={{ mb: 3 }}>
              <Typography variant="h6" color="info.main" gutterBottom>
                Low Confidence Relationships
              </Typography>
              <List>
                {lowConfidenceItems.map((item, index) => (
                  <ListItem key={index} sx={{ border: 1, borderColor: 'info.light', borderRadius: 1, mb: 1 }}>
                    <ListItemIcon>
                      <InfoIcon color="info" />
                    </ListItemIcon>
                    <ListItemText
                      primary={`#${item.id} - ${item.title}`}
                      secondary={
                        <Box>
                          <Typography variant="body2" color="text.secondary">
                            {item.relationshipType} • {item.confidence}
                          </Typography>
                          <Typography variant="body2">
                            {item.reasoning || item.evidence}
                          </Typography>
                        </Box>
                      }
                    />
                  </ListItem>
                ))}
              </List>
            </Box>
          )}
        </AccordionDetails>
      </Accordion>

      {/* Relationship Patterns */}
      {relationshipPatterns.length > 0 && (
        <Accordion 
          expanded={expandedSection === 'patterns'} 
          onChange={handleSectionChange('patterns')}
        >
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="h6">
              🔍 Relationship Patterns Analysis
            </Typography>
          </AccordionSummary>
          <AccordionDetails>
            <List>
              {relationshipPatterns.map((pattern, index) => (
                <ListItem key={index}>
                  <ListItemIcon>
                    <InfoIcon color="primary" />
                  </ListItemIcon>
                  <ListItemText primary={pattern} />
                </ListItem>
              ))}
            </List>
          </AccordionDetails>
        </Accordion>
      )}

      {/* Risk Assessment */}
      {riskAssessment.length > 0 && (
        <Accordion 
          expanded={expandedSection === 'risks'} 
          onChange={handleSectionChange('risks')}
        >
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="h6">
              ⚠️ Risk Assessment
            </Typography>
          </AccordionSummary>
          <AccordionDetails>
            <List>
              {riskAssessment.map((risk, index) => (
                <ListItem key={index}>
                  <ListItemIcon>
                    <WarningIcon color="error" />
                  </ListItemIcon>
                  <ListItemText primary={risk} />
                </ListItem>
              ))}
            </List>
          </AccordionDetails>
        </Accordion>
      )}

      {/* Recommendations */}
      {recommendations.length > 0 && (
        <Accordion 
          expanded={expandedSection === 'recommendations'} 
          onChange={handleSectionChange('recommendations')}
        >
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="h6">
              💡 Recommendations
            </Typography>
          </AccordionSummary>
          <AccordionDetails>
            <List>
              {recommendations.map((recommendation, index) => (
                <ListItem key={index}>
                  <ListItemIcon>
                    <CheckCircleIcon color="success" />
                  </ListItemIcon>
                  <ListItemText primary={recommendation} />
                </ListItem>
              ))}
            </List>
          </AccordionDetails>
        </Accordion>
      )}

      {/* Raw Analysis Results */}
      {analysisResults && (
        <Accordion 
          expanded={expandedSection === 'raw'} 
          onChange={handleSectionChange('raw')}
        >
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="h6">
              📄 Raw Analysis Results
            </Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Paper sx={{ p: 2, bgcolor: 'grey.50' }}>
              <pre style={{ 
                whiteSpace: 'pre-wrap', 
                wordBreak: 'break-word',
                fontSize: '0.875rem',
                fontFamily: 'monospace',
                margin: 0
              }}>
                {typeof analysisResults === 'string' ? analysisResults : JSON.stringify(analysisResults, null, 2)}
              </pre>
            </Paper>
          </AccordionDetails>
        </Accordion>
      )}
    </Box>
  );
};

export default OpenArenaResults;
