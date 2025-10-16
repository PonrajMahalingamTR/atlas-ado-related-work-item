import React from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Paper,
  Chip,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Alert,
  LinearProgress,
  Divider,
  Stack,
} from '@mui/material';
import {
  Assessment as AssessmentIcon,
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon,
  Info as InfoIcon,
  Timeline as TimelineIcon,
  Work as WorkIcon,
  BugReport as BugReportIcon,
  Lightbulb as LightbulbIcon,
  TrendingUp as TrendingUpIcon,
  Security as SecurityIcon,
} from '@mui/icons-material';
import { motion } from 'framer-motion';

const AnalysisInsights = ({ insights, selectedWorkItem }) => {
  // Debug logging
  console.log('AnalysisInsights - Received insights:', insights);
  console.log('AnalysisInsights - Selected work item:', selectedWorkItem);
  
  // Parse structured insights from the updated system prompt
  const parseStructuredInsights = (insights) => {
    if (!insights) return {};
    
    const parsed = {
      risks: [],
      dependencies: [],
      recommendations: [],
      opportunities: []
    };
    
    // Parse risks - handle both old and new format
    if (insights.riskAssessment) {
      if (Array.isArray(insights.riskAssessment)) {
        parsed.risks = insights.riskAssessment.map((risk, index) => {
          if (typeof risk === 'string') {
            // Old format - simple string
            return {
              title: `Risk ${index + 1}`,
              description: risk,
              severity: 'medium',
              impact: 'Potential impact on project',
              mitigation: 'Review and address'
            };
          } else {
            // New format - structured object
            return {
              title: risk.title || `Risk ${index + 1}`,
              description: risk.description || 'Risk identified',
              severity: risk.severity || 'medium',
              impact: risk.impact || 'Potential impact on project',
              mitigation: risk.mitigation || 'Review and address'
            };
          }
        });
      }
    }
    
    // Parse dependencies - handle both old and new format
    if (insights.dependencies) {
      if (Array.isArray(insights.dependencies)) {
        parsed.dependencies = insights.dependencies.map((dep, index) => {
          if (typeof dep === 'string') {
            // Old format - simple string
            return {
              title: `Dependency ${index + 1}`,
              description: dep,
              type: 'medium',
              impact: 'Potential impact on project',
              actionRequired: 'Review and address'
            };
          } else {
            // New format - structured object
            return {
              title: dep.title || `Dependency ${index + 1}`,
              description: dep.description || 'Dependency identified',
              type: dep.type || 'medium',
              impact: dep.impact || 'Potential impact on project',
              actionRequired: dep.actionRequired || 'Review and address'
            };
          }
        });
      }
    }
    
    // Parse recommendations - handle both old and new format
    if (insights.recommendations) {
      if (Array.isArray(insights.recommendations)) {
        parsed.recommendations = insights.recommendations.map((rec, index) => {
          if (typeof rec === 'string') {
            // Old format - simple string
            return {
              title: `Recommendation ${index + 1}`,
              description: rec,
              priority: 'medium',
              rationale: 'Important for project success',
              implementation: 'Review and implement'
            };
          } else {
            // New format - structured object
            return {
              title: rec.title || `Recommendation ${index + 1}`,
              description: rec.description || 'Recommendation provided',
              priority: rec.priority || 'medium',
              rationale: rec.rationale || 'Important for project success',
              implementation: rec.implementation || 'Review and implement'
            };
          }
        });
      }
    }
    
    // Parse opportunities - handle both old and new format
    if (insights.opportunities) {
      if (Array.isArray(insights.opportunities)) {
        parsed.opportunities = insights.opportunities.map((opp, index) => {
          if (typeof opp === 'string') {
            // Old format - simple string
            return {
              title: `Opportunity ${index + 1}`,
              description: opp,
              level: 'medium',
              benefits: 'Potential benefits for project',
              actionRequired: 'Review and implement'
            };
          } else {
            // New format - structured object
            return {
              title: opp.title || `Opportunity ${index + 1}`,
              description: opp.description || 'Opportunity identified',
              level: opp.level || 'medium',
              benefits: opp.benefits || 'Potential benefits for project',
              actionRequired: opp.actionRequired || 'Review and implement'
            };
          }
        });
      }
    }
    
    return parsed;
  };
  
  const structuredInsights = parseStructuredInsights(insights);
  
  const getInsightIcon = (type) => {
    const icons = {
      'risk': <WarningIcon color="error" />,
      'opportunity': <LightbulbIcon color="primary" />,
      'dependency': <TimelineIcon color="info" />,
      'recommendation': <CheckCircleIcon color="success" />,
      'warning': <WarningIcon color="warning" />,
      'info': <InfoIcon color="info" />,
    };
    return icons[type] || <InfoIcon />;
  };

  const getInsightColor = (type) => {
    const colors = {
      'risk': 'error',
      'opportunity': 'primary',
      'dependency': 'info',
      'recommendation': 'success',
      'warning': 'warning',
      'info': 'info',
    };
    return colors[type] || 'info';
  };

  const getSeverityColor = (severity) => {
    const colors = {
      'high': 'error',
      'medium': 'warning',
      'low': 'info',
    };
    return colors[severity] || 'info';
  };

  const getSeverityIcon = (severity) => {
    const icons = {
      'high': <WarningIcon />,
      'medium': <InfoIcon />,
      'low': <CheckCircleIcon />,
    };
    return icons[severity] || <InfoIcon />;
  };

  if (!insights || Object.keys(insights).length === 0) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="info">
          <Typography variant="h6" gutterBottom>
            No Analysis Insights Available
          </Typography>
          <Typography variant="body2">
            The AI analysis did not generate specific insights for this work item.
            This could be due to insufficient data or the work item being too new.
          </Typography>
        </Alert>
      </Box>
    );
  }
  
  // Use structured insights if available, otherwise fall back to original insights
  const displayInsights = structuredInsights.risks.length > 0 || 
                         structuredInsights.dependencies.length > 0 || 
                         structuredInsights.recommendations.length > 0 || 
                         structuredInsights.opportunities.length > 0 
                         ? structuredInsights 
                         : insights;
  
  // Debug logging
  console.log('AnalysisInsights - Structured insights:', structuredInsights);
  console.log('AnalysisInsights - Display insights:', displayInsights);
  console.log('AnalysisInsights - Risks count:', displayInsights.risks?.length || 0);
  console.log('AnalysisInsights - Dependencies count:', displayInsights.dependencies?.length || 0);
  console.log('AnalysisInsights - Recommendations count:', displayInsights.recommendations?.length || 0);
  console.log('AnalysisInsights - Opportunities count:', displayInsights.opportunities?.length || 0);

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h5" gutterBottom>
        AI Analysis Insights
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Intelligent analysis and recommendations based on work item relationships and patterns
      </Typography>

      <Grid container spacing={3}>
        {/* Risk Assessment - First */}
        {displayInsights.risks && displayInsights.risks.length > 0 && (
          <Grid item xs={12} md={6}>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
            >
              <Card elevation={2}>
                <CardContent>
                  <Box display="flex" alignItems="center" gap={1} mb={2}>
                    <WarningIcon color="error" />
                    <Typography variant="h6">
                      Risk Assessment
                    </Typography>
                  </Box>
                  <List>
                    {displayInsights.risks.map((risk, index) => (
                      <ListItem key={index} sx={{ px: 0, flexDirection: 'column', alignItems: 'stretch' }}>
                        <Box display="flex" alignItems="center" gap={1} mb={1}>
                          <ListItemIcon sx={{ minWidth: 'auto', mr: 1 }}>
                            {getSeverityIcon(risk.severity)}
                          </ListItemIcon>
                          <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>
                            {risk.title}
                          </Typography>
                          <Chip
                            icon={getSeverityIcon(risk.severity)}
                            label={risk.severity.toUpperCase()}
                            size="small"
                            color={getSeverityColor(risk.severity)}
                            variant="outlined"
                          />
                        </Box>
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                          {risk.description}
                        </Typography>
                        {risk.impact && (
                          <Box sx={{ mb: 1 }}>
                            <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 'bold' }}>
                              Impact:
                            </Typography>
                            <Typography variant="body2" color="text.secondary" sx={{ ml: 1 }}>
                              {risk.impact}
                            </Typography>
                          </Box>
                        )}
                        {risk.mitigation && (
                          <Box>
                            <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 'bold' }}>
                              Mitigation:
                            </Typography>
                            <Typography variant="body2" color="text.secondary" sx={{ ml: 1 }}>
                              {risk.mitigation}
                            </Typography>
                          </Box>
                        )}
                        {index < displayInsights.risks.length - 1 && <Divider sx={{ mt: 2 }} />}
                      </ListItem>
                    ))}
                  </List>
                </CardContent>
              </Card>
            </motion.div>
          </Grid>
        )}

        {/* Dependencies - Second */}
        {displayInsights.dependencies && displayInsights.dependencies.length > 0 && (
          <Grid item xs={12} md={6}>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.1 }}
            >
              <Card elevation={2}>
                <CardContent>
                  <Box display="flex" alignItems="center" gap={1} mb={2}>
                    <TimelineIcon color="info" />
                    <Typography variant="h6">
                      Dependencies
                    </Typography>
                  </Box>
                  <List>
                    {displayInsights.dependencies.map((dep, index) => (
                      <ListItem key={index} sx={{ px: 0, flexDirection: 'column', alignItems: 'stretch' }}>
                        <Box display="flex" alignItems="center" gap={1} mb={1}>
                          <ListItemIcon sx={{ minWidth: 'auto', mr: 1 }}>
                            <TimelineIcon color="info" />
                          </ListItemIcon>
                          <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>
                            {dep.title}
                          </Typography>
                          <Chip
                            label={dep.type.toUpperCase()}
                            size="small"
                            color="info"
                            variant="outlined"
                          />
                        </Box>
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                          {dep.description}
                        </Typography>
                        {dep.impact && (
                          <Box sx={{ mb: 1 }}>
                            <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 'bold' }}>
                              Impact:
                            </Typography>
                            <Typography variant="body2" color="text.secondary" sx={{ ml: 1 }}>
                              {dep.impact}
                            </Typography>
                          </Box>
                        )}
                        {dep.actionRequired && (
                          <Box>
                            <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 'bold' }}>
                              Action Required:
                            </Typography>
                            <Typography variant="body2" color="text.secondary" sx={{ ml: 1 }}>
                              {dep.actionRequired}
                            </Typography>
                          </Box>
                        )}
                        {index < displayInsights.dependencies.length - 1 && <Divider sx={{ mt: 2 }} />}
                      </ListItem>
                    ))}
                  </List>
                </CardContent>
              </Card>
            </motion.div>
          </Grid>
        )}

        {/* Recommendations - Third */}
        {displayInsights.recommendations && displayInsights.recommendations.length > 0 && (
          <Grid item xs={12} md={6}>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.2 }}
            >
              <Card elevation={2}>
                <CardContent>
                  <Box display="flex" alignItems="center" gap={1} mb={2}>
                    <CheckCircleIcon color="success" />
                    <Typography variant="h6">
                      Recommendations
                    </Typography>
                  </Box>
                  <List>
                    {displayInsights.recommendations.map((rec, index) => (
                      <ListItem key={index} sx={{ px: 0, flexDirection: 'column', alignItems: 'stretch' }}>
                        <Box display="flex" alignItems="center" gap={1} mb={1}>
                          <ListItemIcon sx={{ minWidth: 'auto', mr: 1 }}>
                            <CheckCircleIcon color="success" />
                          </ListItemIcon>
                          <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>
                            {rec.title}
                          </Typography>
                          {rec.priority && (
                            <Chip
                              label={rec.priority.toUpperCase()}
                              size="small"
                              color="success"
                              variant="outlined"
                            />
                          )}
                        </Box>
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                          {rec.description}
                        </Typography>
                        {rec.rationale && (
                          <Box sx={{ mb: 1 }}>
                            <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 'bold' }}>
                              Rationale:
                            </Typography>
                            <Typography variant="body2" color="text.secondary" sx={{ ml: 1 }}>
                              {rec.rationale}
                            </Typography>
                          </Box>
                        )}
                        {rec.implementation && (
                          <Box>
                            <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 'bold' }}>
                              Implementation:
                            </Typography>
                            <Typography variant="body2" color="text.secondary" sx={{ ml: 1 }}>
                              {rec.implementation}
                            </Typography>
                          </Box>
                        )}
                        {index < displayInsights.recommendations.length - 1 && <Divider sx={{ mt: 2 }} />}
                      </ListItem>
                    ))}
                  </List>
                </CardContent>
              </Card>
            </motion.div>
          </Grid>
        )}

        {/* Opportunities - Fourth */}
        {displayInsights.opportunities && displayInsights.opportunities.length > 0 && (
          <Grid item xs={12} md={6}>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.3 }}
            >
              <Card elevation={2}>
                <CardContent>
                  <Box display="flex" alignItems="center" gap={1} mb={2}>
                    <LightbulbIcon color="primary" />
                    <Typography variant="h6">
                      Opportunities
                    </Typography>
                  </Box>
                  <List>
                    {displayInsights.opportunities.map((opportunity, index) => (
                      <ListItem key={index} sx={{ px: 0, flexDirection: 'column', alignItems: 'stretch' }}>
                        <Box display="flex" alignItems="center" gap={1} mb={1}>
                          <ListItemIcon sx={{ minWidth: 'auto', mr: 1 }}>
                            <LightbulbIcon color="primary" />
                          </ListItemIcon>
                          <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>
                            {opportunity.title}
                          </Typography>
                          {opportunity.level && (
                            <Chip
                              label={opportunity.level.toUpperCase()}
                              size="small"
                              color="primary"
                              variant="outlined"
                            />
                          )}
                        </Box>
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                          {opportunity.description}
                        </Typography>
                        {opportunity.benefits && (
                          <Box sx={{ mb: 1 }}>
                            <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 'bold' }}>
                              Benefits:
                            </Typography>
                            <Typography variant="body2" color="text.secondary" sx={{ ml: 1 }}>
                              {opportunity.benefits}
                            </Typography>
                          </Box>
                        )}
                        {opportunity.actionRequired && (
                          <Box>
                            <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 'bold' }}>
                              Action Required:
                            </Typography>
                            <Typography variant="body2" color="text.secondary" sx={{ ml: 1 }}>
                              {opportunity.actionRequired}
                            </Typography>
                          </Box>
                        )}
                        {index < displayInsights.opportunities.length - 1 && <Divider sx={{ mt: 2 }} />}
                      </ListItem>
                    ))}
                  </List>
                </CardContent>
              </Card>
            </motion.div>
          </Grid>
        )}

        {/* Summary Statistics */}
        {displayInsights.summary && (
          <Grid item xs={12}>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.4 }}
            >
              <Card elevation={2}>
                <CardContent>
                  <Typography variant="h6" gutterBottom>
                    Analysis Summary
                  </Typography>
                  <Grid container spacing={2}>
                    {displayInsights.summary.totalRelatedItems && (
                      <Grid item xs={12} sm={6} md={3}>
                        <Paper elevation={1} sx={{ p: 2, textAlign: 'center' }}>
                          <Typography variant="h4" color="primary">
                            {displayInsights.summary.totalRelatedItems}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            Related Items
                          </Typography>
                        </Paper>
                      </Grid>
                    )}
                    {displayInsights.summary.highConfidenceItems && (
                      <Grid item xs={12} sm={6} md={3}>
                        <Paper elevation={1} sx={{ p: 2, textAlign: 'center' }}>
                          <Typography variant="h4" color="success.main">
                            {displayInsights.summary.highConfidenceItems}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            High Confidence
                          </Typography>
                        </Paper>
                      </Grid>
                    )}
                    {displayInsights.summary.risksIdentified && (
                      <Grid item xs={12} sm={6} md={3}>
                        <Paper elevation={1} sx={{ p: 2, textAlign: 'center' }}>
                          <Typography variant="h4" color="error.main">
                            {displayInsights.summary.risksIdentified}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            Risks Identified
                          </Typography>
                        </Paper>
                      </Grid>
                    )}
                    {displayInsights.summary.opportunitiesFound && (
                      <Grid item xs={12} sm={6} md={3}>
                        <Paper elevation={1} sx={{ p: 2, textAlign: 'center' }}>
                          <Typography variant="h4" color="primary.main">
                            {displayInsights.summary.opportunitiesFound}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            Opportunities
                          </Typography>
                        </Paper>
                      </Grid>
                    )}
                  </Grid>
                </CardContent>
              </Card>
            </motion.div>
          </Grid>
        )}
      </Grid>
    </Box>
  );
};

export default AnalysisInsights;
