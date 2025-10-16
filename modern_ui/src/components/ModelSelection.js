import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Paper,
  Typography,
  Grid,
  Card,
  CardContent,
  CardActions,
  Button,
  Alert,
  CircularProgress,
  Chip,
  Radio,
  RadioGroup,
  FormControlLabel,
  FormControl,
  FormLabel,
  Switch,
  Divider,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemText,
} from '@mui/material';
import {
  CheckCircle as SelectedIcon,
  Speed as PerformanceIcon,
  AccountBalance as CostIcon,
  Star as CapabilityIcon,
  SmartToy as DefaultModelIcon,
  AutoAwesome as AutoSelectIcon,
  ExpandMore as ExpandMoreIcon,
  Settings as SettingsIcon,
  Preview as PreviewIcon,
  Psychology as QualityIcon,
  Code as CodingIcon,
  Balance as BalancedIcon,
} from '@mui/icons-material';

import {
  fetchAvailableModels,
  fetchCurrentModel,
  selectModel,
  autoSelectModel,
  previewAutoSelection,
  fetchAutoSelectionSettings,
  updateAutoSelectionSettings,
  analyzeWorkItemComplexity,
  formatApiError,
} from '../services/api';

// Helper function to get model display name from model ID
const getModelDisplayName = (modelId) => {
  const modelNames = {
    'claude-4.1-opus': 'Claude 4.1 Opus',
    'gpt-5': 'GPT-5',
    'gemini-2.5-pro': 'Gemini 2.5 Pro',
    'llama-3-70b': 'Llama 3 70b',
    // Legacy model IDs for backward compatibility
    'claude-4-opus': 'Claude 4.1 Opus',
    'gemini-2-pro': 'Gemini 2.5 Pro'
  };
  return modelNames[modelId] || modelId || 'Not specified';
};

// Custom company logo component
const CompanyLogo = ({ modelId, sx }) => {
  const logoMap = {
    'claude-4.1-opus': '/icons/anthropic.png',
    'gpt-5': '/icons/openai.png',
    'gemini-2.5-pro': '/icons/google.png',
    'llama-3-70b': '/icons/meta.png',
    // Legacy model IDs for backward compatibility
    'claude-4-opus': '/icons/anthropic.png',
    'gemini-2-pro': '/icons/google.png'
  };

  const logoSrc = logoMap[modelId];
  
  if (logoSrc) {
    return (
      <Box
        component="img"
        src={logoSrc}
        alt={`${modelId} logo`}
        sx={{
          width: sx?.fontSize || 24,
          height: sx?.fontSize || 24,
          ...sx,
          filter: sx?.filter || 'none'
        }}
      />
    );
  }

  // Fallback to default Material-UI icon
  return <DefaultModelIcon sx={sx} />;
};


// Helper function to get model-specific styling for logos
const getModelLogoProps = (modelId, isSelected) => {
  const baseSize = isSelected ? 28 : 24;
  
  return {
    modelId,
    sx: {
      mr: 2,
      fontSize: baseSize,
      width: baseSize,
      height: baseSize,
      borderRadius: '4px',
      // Add subtle glow effect when selected
      boxShadow: isSelected ? '0 0 8px rgba(0,0,0,0.3)' : 'none',
      transition: 'all 0.3s ease-in-out',
      '&:hover': {
        transform: 'scale(1.05)',
      }
    }
  };
};

const ModelSelection = ({ connectionStatus }) => {
  const [loading, setLoading] = useState({
    models: false,
    selection: false,
    autoSelection: false,
    preview: false,
  });
  
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  
  const [availableModels, setAvailableModels] = useState([]);
  const [currentModel, setCurrentModel] = useState('');
  const [selectedModel, setSelectedModel] = useState('');
  
  // Auto-selection state
  const [autoSelectionEnabled, setAutoSelectionEnabled] = useState(false);
  const [userPriority, setUserPriority] = useState('balanced');
  const [previewResult, setPreviewResult] = useState(null);
  const [showPreviewDialog, setShowPreviewDialog] = useState(false);
  const [autoSelectionSettings, setAutoSelectionSettings] = useState({
    enabled: false,
    user_priority: 'balanced',
    fallback_model: 'claude-4.1-opus'
  });

  useEffect(() => {
    if (connectionStatus.azure_devops.connected) {
      loadData();
    }
  }, [connectionStatus.azure_devops.connected]);

  const loadData = async () => {
    try {
      setLoading(prev => ({ ...prev, models: true }));
      
      const [modelsData, currentModelData] = await Promise.all([
        fetchAvailableModels(),
        fetchCurrentModel(),
      ]);
      
      setAvailableModels(modelsData || []);
      
      // Set current model with fallback to default
      const currentModelId = currentModelData?.model;
      let modelToSet = currentModelId;
      
      // If no model is currently selected, set Claude 4.1 Opus as default
      if (!currentModelId && modelsData && modelsData.length > 0) {
        // Try to find Claude 4.1 Opus first, otherwise use the first available model
        const defaultModel = modelsData.find(m => m.id === 'claude-4.1-opus') || modelsData[0];
        modelToSet = defaultModel.id;
        
        // Auto-select the default model on the backend
        try {
          await selectModel(modelToSet);
        } catch (error) {
          console.warn('Failed to auto-select default model:', error);
        }
      }
      
      setCurrentModel(modelToSet || '');
      setSelectedModel(modelToSet || '');
      
    } catch (err) {
      const formattedError = formatApiError(err);
      setError(formattedError.message);
    } finally {
      setLoading(prev => ({ ...prev, models: false }));
    }
  };

  const handleModelSelect = async (modelId) => {
    try {
      setLoading(prev => ({ ...prev, selection: true }));
      setError('');
      setSuccess('');
      
      const response = await selectModel(modelId);
      
      if (response.success) {
        setCurrentModel(modelId);
        setSelectedModel(modelId);
        setSuccess(`Successfully selected model: ${response.model}`);
      } else {
        setError(response.error || 'Failed to select model');
      }
      
    } catch (err) {
      const formattedError = formatApiError(err);
      setError(formattedError.message);
    } finally {
      setLoading(prev => ({ ...prev, selection: false }));
    }
  };

  // Auto-selection functions
  const loadAutoSelectionSettings = async () => {
    try {
      const settings = await fetchAutoSelectionSettings();
      setAutoSelectionSettings(settings);
      setAutoSelectionEnabled(settings.enabled);
      setUserPriority(settings.user_priority);
    } catch (err) {
      console.error('Failed to load auto-selection settings:', err);
    }
  };

  const handleAutoSelectionToggle = async (enabled) => {
    try {
      setAutoSelectionEnabled(enabled);
      const updatedSettings = { ...autoSelectionSettings, enabled };
      await updateAutoSelectionSettings(updatedSettings);
      setAutoSelectionSettings(updatedSettings);
      
      if (enabled) {
        setSuccess('Auto-selection enabled! Models will be automatically selected based on work item analysis.');
      } else {
        setSuccess('Auto-selection disabled. You can now manually select models.');
      }
    } catch (err) {
      const formattedError = formatApiError(err);
      setError(formattedError.message);
      setAutoSelectionEnabled(!enabled); // Revert on error
    }
  };

  const handlePriorityChange = async (priority) => {
    try {
      setUserPriority(priority);
      const updatedSettings = { ...autoSelectionSettings, user_priority: priority };
      await updateAutoSelectionSettings(updatedSettings);
      setAutoSelectionSettings(updatedSettings);
    } catch (err) {
      const formattedError = formatApiError(err);
      setError(formattedError.message);
    }
  };

  const handleAutoSelectWithWorkItems = async (workItems) => {
    try {
      setLoading(prev => ({ ...prev, autoSelection: true }));
      setError('');
      setSuccess('');
      
      const response = await autoSelectModel(workItems, userPriority);
      
      if (response.success) {
        setCurrentModel(response.selected_model);
        setSelectedModel(response.selected_model);
        setSuccess(`Auto-selected ${getModelDisplayName(response.selected_model)} based on work item analysis: ${response.reasoning.overall_complexity} complexity, ${response.reasoning.work_item_count} items`);
      } else {
        setError(response.error || 'Auto-selection failed');
      }
    } catch (err) {
      const formattedError = formatApiError(err);
      setError(formattedError.message);
    } finally {
      setLoading(prev => ({ ...prev, autoSelection: false }));
    }
  };

  const handlePreviewAutoSelection = async (workItems) => {
    try {
      setLoading(prev => ({ ...prev, preview: true }));
      setError('');
      
      const response = await previewAutoSelection(workItems, userPriority);
      setPreviewResult(response);
      setShowPreviewDialog(true);
    } catch (err) {
      const formattedError = formatApiError(err);
      setError(formattedError.message);
    } finally {
      setLoading(prev => ({ ...prev, preview: false }));
    }
  };

  // Load auto-selection settings on component mount
  useEffect(() => {
    if (connectionStatus.azure_devops.connected) {
      loadAutoSelectionSettings();
    }
  }, [connectionStatus.azure_devops.connected]);

  const getModelDetails = (modelId) => {
    const modelDetails = {
      'gpt-5': {
        performance: 'Fast',
        cost: 'Medium',
        capability: 'Smartest',
        oneLiner: 'Smartest, fastest, most useful model',
        description: '74.9% on SWE-bench Verified and state-of-the-art performance across coding, math, writing. Unified system with smart model and deeper reasoning.',
        costDetails: '$1.25 input / $10 output per million tokens',
        coreCapability: 'Coding collaborator excelling at high-quality code',
        pros: ['Aggressively competitive pricing', 'Superior coding', 'Reduced hallucinations', 'Fast with built-in reasoning'],
        cons: ['Reasoning tokens count as output'],
      },
      'gpt-3.5-turbo': {
        performance: 'Fast',
        cost: 'Low',
        capability: 'Good',
        description: 'Fast and cost-effective model suitable for basic work item analysis and relationship detection.',
        pros: ['Fast response', 'Cost-effective', 'Good for basic analysis'],
        cons: ['Less detailed insights', 'Simpler reasoning'],
      },
      'claude-4.1-opus': {
        performance: '44.3 tokens/sec',
        cost: 'Very High',
        capability: 'Most Intelligent',
        oneLiner: 'Most intelligent model to date',
        description: 'Hybrid reasoning model in one with 200,000 token context window. Leader on SWE-bench for complex coding tasks.',
        costDetails: '$15 input / $75 output per million tokens',
        coreCapability: 'Complex agent applications and coding',
        pros: ['74.5% SWE-bench score', 'Extended thinking mode', '32K output support', '200K token context'],
        cons: ['Expensive', 'Slower than average'],
      },
      'claude-3-sonnet': {
        performance: 'Medium',
        cost: 'Medium',
        capability: 'Very Good',
        description: 'Balanced performance model offering good analysis quality at reasonable cost and speed.',
        pros: ['Balanced performance', 'Good cost-speed ratio', 'Reliable analysis'],
        cons: ['Not the most advanced', 'Medium capability'],
      },
      'gemini-2.5-pro': {
        performance: 'Fast',
        cost: 'Medium',
        capability: 'Most Advanced for Coding',
        oneLiner: 'Most advanced model for coding',
        description: 'Most advanced reasoning Gemini model with 1-million token context window. Capable of reasoning through thoughts before responding.',
        costDetails: '$1.25 input / $10 output (under 200K tokens)',
        coreCapability: 'Development work, code generation, large-scale automation',
        pros: ['Massive context window (1M tokens)', 'Native multimodality', 'Competitive pricing', 'Adjustable thinking budgets'],
        cons: ['Reasoning tokens included in output count'],
      },
      'llama-3-70b': {
        performance: '42.2 tokens/sec',
        cost: 'Low',
        capability: 'Most Capable Open Model',
        oneLiner: 'Most capable openly available LLM',
        description: '70B parameter open model with 128K token vocabulary. Optimized for dialogue/chat use cases.',
        costDetails: '~$0.73 input / $0.84 output per million tokens',
        coreCapability: 'Conversational AI, code generation, text summarization',
        pros: ['Open source', 'Very affordable', 'Commercially licensed', 'Good performance'],
        cons: ['Smaller context window (8K)', 'Lower performance vs. proprietary models'],
      },
    };
    
    return modelDetails[modelId] || {
      performance: 'Unknown',
      cost: 'Unknown',
      capability: 'Unknown',
      description: 'Model information not available.',
      pros: [],
      cons: [],
    };
  };

  if (!connectionStatus.azure_devops.connected) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Alert severity="warning">
          Please connect to Azure DevOps first to configure model selection.
        </Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" component="h1" fontWeight={600} gutterBottom>
          Intelligent AI Model Selection
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Intelligently select the perfect AI model for your work item analysis. Let our smart system recommend the optimal model based on your needs.
        </Typography>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert severity="success" sx={{ mb: 3 }}>
          {success}
        </Alert>
      )}

      {/* Current Selection */}
      {currentModel && (
        <Paper sx={{ p: 3, mb: 4, backgroundColor: 'primary.50' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            <SelectedIcon sx={{ mr: 2, color: 'primary.main' }} />
            <Typography variant="h6" color="primary.main">
              Currently Selected: {getModelDisplayName(currentModel)}
            </Typography>
          </Box>
          <Typography variant="body2" color="text.secondary">
            This model will be used for all work item analysis and relationship detection.
          </Typography>
        </Paper>
      )}

      {/* Auto-Selection Control Panel */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Accordion expanded={autoSelectionEnabled} onChange={(event, expanded) => setAutoSelectionEnabled(expanded)}>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Box sx={{ display: 'flex', alignItems: 'center', width: '100%' }}>
              <AutoSelectIcon sx={{ mr: 2, color: 'primary.main' }} />
              <Typography variant="h6" sx={{ flexGrow: 1 }}>
                Smart Model Auto-Selection
              </Typography>
              <Switch
                checked={autoSelectionEnabled}
                onChange={(e) => {
                  e.stopPropagation();
                  handleAutoSelectionToggle(e.target.checked);
                }}
                size="small"
                color="primary"
                sx={{ mr: 1 }}
              />
            </Box>
          </AccordionSummary>
          <AccordionDetails>
            <Box sx={{ mb: 3 }}>
              <Typography variant="body2" color="text.secondary" paragraph>
                Let AI automatically choose the best model based on your work items' complexity, type, and your priorities.
              </Typography>
              
              {/* Priority Selection */}
              <FormControl component="fieldset" sx={{ mb: 2 }}>
                <FormLabel component="legend" sx={{ mb: 1, fontSize: '0.875rem', fontWeight: 600 }}>
                  Selection Priority
                </FormLabel>
                <RadioGroup
                  row
                  value={userPriority}
                  onChange={(e) => handlePriorityChange(e.target.value)}
                  sx={{ gap: 2 }}
                >
                  <FormControlLabel
                    value="speed"
                    control={<Radio size="small" />}
                    label={
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        <PerformanceIcon sx={{ fontSize: 16, mr: 0.5 }} />
                        Speed
                      </Box>
                    }
                  />
                  <FormControlLabel
                    value="cost"
                    control={<Radio size="small" />}
                    label={
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        <CostIcon sx={{ fontSize: 16, mr: 0.5 }} />
                        Cost
                      </Box>
                    }
                  />
                  <FormControlLabel
                    value="quality"
                    control={<Radio size="small" />}
                    label={
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        <QualityIcon sx={{ fontSize: 16, mr: 0.5 }} />
                        Quality
                      </Box>
                    }
                  />
                  <FormControlLabel
                    value="coding"
                    control={<Radio size="small" />}
                    label={
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        <CodingIcon sx={{ fontSize: 16, mr: 0.5 }} />
                        Coding
                      </Box>
                    }
                  />
                  <FormControlLabel
                    value="balanced"
                    control={<Radio size="small" />}
                    label={
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        <BalancedIcon sx={{ fontSize: 16, mr: 0.5 }} />
                        Balanced
                      </Box>
                    }
                  />
                </RadioGroup>
              </FormControl>

              {/* Action Buttons */}
              <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                <Button
                  variant="outlined"
                  size="small"
                  startIcon={loading.preview ? <CircularProgress size={16} /> : <PreviewIcon />}
                  onClick={() => handlePreviewAutoSelection([{ fields: { 'System.WorkItemType': 'User Story', 'System.Title': 'Sample work item', 'System.Description': 'Sample description for testing auto-selection' } }])}
                  disabled={loading.preview}
                >
                  {loading.preview ? 'Previewing...' : 'Preview Selection'}
                </Button>
                <Button
                  variant="contained"
                  size="small"
                  startIcon={loading.autoSelection ? <CircularProgress size={16} /> : <AutoSelectIcon />}
                  onClick={() => handleAutoSelectWithWorkItems([{ fields: { 'System.WorkItemType': 'User Story', 'System.Title': 'Sample work item', 'System.Description': 'Sample description for testing auto-selection' } }])}
                  disabled={loading.autoSelection}
                  sx={{ 
                    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                    color: 'white',
                    '&:hover': {
                      background: 'linear-gradient(135deg, #5a6fd8 0%, #6a4190 100%)',
                    }
                  }}
                >
                  {loading.autoSelection ? 'Selecting...' : 'Auto-Select Now'}
                </Button>
              </Box>

              <Typography variant="caption" color="text.secondary" sx={{ mt: 2, display: 'block' }}>
                💡 <strong>How it works:</strong> We analyze work item type, complexity, description length, story points, and technical keywords to choose the optimal model based on your priority.
              </Typography>
            </Box>
          </AccordionDetails>
        </Accordion>
      </Paper>

      {/* Preview Dialog */}
      <Dialog open={showPreviewDialog} onClose={() => setShowPreviewDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Auto-Selection Preview</DialogTitle>
        <DialogContent>
          {previewResult && (
            <Box>
              <Typography variant="h6" color="primary" gutterBottom>
                Recommended: {getModelDisplayName(previewResult.preview_model)}
              </Typography>
              
              {previewResult.reasoning && (
                <Box sx={{ mt: 2 }}>
                  <Typography variant="subtitle2" gutterBottom>Selection Reasoning:</Typography>
                  <List dense>
                    <ListItem>
                      <ListItemText 
                        primary="Work Items"
                        secondary={`${previewResult.reasoning.work_item_count} items analyzed`}
                      />
                    </ListItem>
                    <ListItem>
                      <ListItemText 
                        primary="Primary Type"
                        secondary={previewResult.reasoning.primary_type}
                      />
                    </ListItem>
                    <ListItem>
                      <ListItemText 
                        primary="Complexity Level"
                        secondary={`${previewResult.reasoning.overall_complexity} (score: ${previewResult.reasoning.avg_complexity_score})`}
                      />
                    </ListItem>
                    <ListItem>
                      <ListItemText 
                        primary="Your Priority"
                        secondary={previewResult.reasoning.user_priority}
                      />
                    </ListItem>
                  </List>
                </Box>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowPreviewDialog(false)}>Close</Button>
          {previewResult?.preview_model && (
            <Button 
              variant="contained" 
              onClick={() => {
                handleModelSelect(previewResult.preview_model);
                setShowPreviewDialog(false);
              }}
              sx={{
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                color: 'white',
                '&:hover': {
                  background: 'linear-gradient(135deg, #5a6fd8 0%, #6a4190 100%)',
                }
              }}
            >
              Select {getModelDisplayName(previewResult.preview_model)}
            </Button>
          )}
        </DialogActions>
      </Dialog>

      {loading.models ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
          <CircularProgress size={60} />
        </Box>
      ) : (
        <Grid container spacing={3}>
          {availableModels.map((model) => {
            const isSelected = currentModel === model.id;
            const isBeingSelected = loading.selection && selectedModel === model.id;
            const details = getModelDetails(model.id);
            
            return (
              <Grid item xs={12} md={6} key={model.id}>
                <Card 
                  sx={{ 
                    height: '100%',
                    border: isSelected ? 3 : 1,
                    borderColor: isSelected ? 'primary.main' : 'divider',
                    backgroundColor: isSelected ? 'primary.50' : 'background.paper',
                    boxShadow: isSelected ? '0 8px 32px rgba(25, 118, 210, 0.15)' : 1,
                    transform: isSelected ? 'scale(1.02)' : 'scale(1)',
                    transition: 'all 0.3s ease-in-out',
                    position: 'relative',
                    '&:hover': {
                      boxShadow: isSelected ? '0 12px 40px rgba(25, 118, 210, 0.25)' : 3,
                      transform: isSelected ? 'scale(1.02)' : 'scale(1.01)',
                    }
                  }}
                >
                  {isSelected && (
                    <Chip
                      label="Currently Active"
                      color="primary"
                      variant="filled"
                      size="small"
                      sx={{
                        position: 'absolute',
                        top: 12,
                        right: 12,
                        zIndex: 1,
                        fontWeight: 600,
                        fontSize: '0.75rem',
                        backgroundColor: 'primary.main',
                        color: 'white',
                        boxShadow: '0 2px 8px rgba(25, 118, 210, 0.3)',
                        '& .MuiChip-label': {
                          paddingX: 1.5,
                        }
                      }}
                    />
                  )}
                  
                  <CardContent sx={{ pb: 1 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                      <CompanyLogo {...getModelLogoProps(model.id, isSelected)} />
                      <Typography 
                        variant="h6" 
                        component="h3"
                        sx={{
                          color: isSelected ? 'primary.dark' : 'text.primary',
                          fontWeight: isSelected ? 700 : 500,
                        }}
                      >
                        {model.name}
                      </Typography>
                    </Box>
                    
                    {/* One-liner */}
                    {details.oneLiner && (
                      <Typography variant="subtitle2" color="primary.main" sx={{ mb: 1, fontWeight: 600 }}>
                        {details.oneLiner}
                      </Typography>
                    )}
                    
                    <Typography variant="body2" sx={{ mb: 2 }}>
                      {details.description}
                    </Typography>

                    {/* Core Capability */}
                    {details.coreCapability && (
                      <Typography variant="caption" color="text.secondary" sx={{ mb: 2, display: 'block' }}>
                        <strong>Core Capability:</strong> {details.coreCapability}
                      </Typography>
                    )}

                    {/* Cost Details */}
                    {details.costDetails && (
                      <Typography variant="caption" color="text.secondary" sx={{ mb: 2, display: 'block' }}>
                        <strong>Pricing:</strong> {details.costDetails}
                      </Typography>
                    )}

                    {/* Performance Indicators */}
                    <Box sx={{ display: 'flex', gap: 1, mb: 2, flexWrap: 'wrap' }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', mr: 2 }}>
                        <PerformanceIcon sx={{ mr: 0.5, fontSize: 16, color: 'text.secondary' }} />
                        <Typography variant="caption" color="text.secondary">
                          Speed: {details.performance}
                        </Typography>
                      </Box>
                      
                      <Box sx={{ display: 'flex', alignItems: 'center', mr: 2 }}>
                        <CostIcon sx={{ mr: 0.5, fontSize: 16, color: 'text.secondary' }} />
                        <Typography variant="caption" color="text.secondary">
                          Cost: {details.cost}
                        </Typography>
                      </Box>
                      
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        <CapabilityIcon sx={{ mr: 0.5, fontSize: 16, color: 'text.secondary' }} />
                        <Typography variant="caption" color="text.secondary">
                          Capability: {details.capability}
                        </Typography>
                      </Box>
                    </Box>

                    {/* Pros and Cons */}
                    <Grid container spacing={2}>
                      <Grid item xs={6}>
                        <Typography variant="caption" color="success.main" fontWeight={600}>
                          Pros:
                        </Typography>
                        <Typography variant="caption" display="block" color="text.secondary">
                          {details.pros.join(', ')}
                        </Typography>
                      </Grid>
                      <Grid item xs={6}>
                        <Typography variant="caption" color="warning.main" fontWeight={600}>
                          Cons:
                        </Typography>
                        <Typography variant="caption" display="block" color="text.secondary">
                          {details.cons.join(', ')}
                        </Typography>
                      </Grid>
                    </Grid>
                  </CardContent>

                  <CardActions sx={{ px: 2, pb: 2 }}>
                    <Button
                      fullWidth
                      variant={isSelected ? "contained" : "contained"}
                      disabled={isSelected || loading.selection}
                      onClick={() => handleModelSelect(model.id)}
                      startIcon={isBeingSelected ? <CircularProgress size={16} /> : (isSelected ? <SelectedIcon /> : null)}
                      sx={{
                        background: isSelected ? 'linear-gradient(135deg, #10b981 0%, #059669 100%)' : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                        color: 'white',
                        fontWeight: 600,
                        '&:hover': {
                          background: isSelected ? 'linear-gradient(135deg, #059669 0%, #047857 100%)' : 'linear-gradient(135deg, #5a6fd8 0%, #6a4190 100%)',
                        },
                        '&.Mui-disabled': {
                          background: isSelected ? 'linear-gradient(135deg, #10b981 0%, #059669 100%)' : 'rgba(0,0,0,0.12)',
                          color: 'white',
                        }
                      }}
                    >
                      {isSelected 
                        ? "Currently Active" 
                        : isBeingSelected 
                          ? "Selecting..." 
                          : "Select Model"
                      }
                    </Button>
                  </CardActions>
                </Card>
              </Grid>
            );
          })}
        </Grid>
      )}

      {/* Model Comparison */}
      <Paper sx={{ mt: 4, p: 3 }}>
        <Typography variant="h6" gutterBottom>
          Intelligent Model Selection Guide
        </Typography>
        
        <Grid container spacing={3}>
          <Grid item xs={12} md={3}>
            <Typography variant="subtitle2" color="primary" gutterBottom>
              Most Intelligent & Advanced
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Choose <strong>Claude 4.1 Opus</strong> for the most intelligent analysis with 200K context window and superior SWE-bench performance. Best for complex agent applications.
            </Typography>
          </Grid>
          
          <Grid item xs={12} md={3}>
            <Typography variant="subtitle2" color="primary" gutterBottom>
              Smart & Fast Coding
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Choose <strong>GPT-5</strong> for the smartest, fastest model with competitive pricing and superior coding capabilities. Built-in reasoning at great value.
            </Typography>
          </Grid>
          
          <Grid item xs={12} md={3}>
            <Typography variant="subtitle2" color="primary" gutterBottom>
              Massive Context & Multimodal
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Choose <strong>Gemini 2.5 Pro</strong> for 1M token context window, native multimodality, and advanced reasoning for large-scale automation.
            </Typography>
          </Grid>
          
          <Grid item xs={12} md={3}>
            <Typography variant="subtitle2" color="primary" gutterBottom>
              Open Source & Affordable
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Choose <strong>Llama 3 70b</strong> for the most capable open-source model with commercial licensing and very affordable pricing.
            </Typography>
          </Grid>
        </Grid>
      </Paper>
    </Container>
  );
};

export default ModelSelection;

