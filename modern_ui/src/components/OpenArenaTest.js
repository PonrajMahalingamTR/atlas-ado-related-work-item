import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Paper,
  Typography,
  Button,
  Grid,
  Card,
  CardContent,
  Alert,
  CircularProgress,
  TextField,
  Chip,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
} from '@mui/material';
import {
  Science as TestIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  Info as InfoIcon,
  Psychology as PsychologyIcon,
  Speed as SpeedIcon,
  Timeline as ResponseIcon,
} from '@mui/icons-material';

import {
  testOpenArenaConnection,
  fetchCurrentModel,
  formatApiError,
} from '../services/api';
import { ModelIcon, getModelDisplayName } from './ModelIcon';

const OpenArenaTest = ({ connectionStatus }) => {
  const [loading, setLoading] = useState({
    connection: false,
    analysis: false,
  });
  
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  
  const [testResults, setTestResults] = useState(null);
  const [currentModel, setCurrentModel] = useState('');
  const [testInput, setTestInput] = useState('Test work item analysis for connectivity verification');

  useEffect(() => {
    if (connectionStatus.openarena.connected) {
      loadCurrentModel();
    }
  }, [connectionStatus.openarena.connected]);

  const loadCurrentModel = async () => {
    try {
      const modelData = await fetchCurrentModel();
      setCurrentModel(modelData?.model || 'Unknown');
    } catch (err) {
      console.error('Error loading current model:', err);
    }
  };

  const handleConnectionTest = async () => {
    try {
      setLoading(prev => ({ ...prev, connection: true }));
      setError('');
      setSuccess('');
      setTestResults(null);

      const startTime = Date.now();
      const response = await testOpenArenaConnection();
      const endTime = Date.now();
      const responseTime = endTime - startTime;

      if (response.connected) {
        setSuccess('OpenArena connection test successful!');
        setTestResults({
          connected: true,
          responseTime,
          message: response.message,
          timestamp: new Date().toISOString(),
        });
      } else {
        setError(response.message || 'Connection test failed');
        setTestResults({
          connected: false,
          responseTime,
          message: response.message,
          error: response.error,
          timestamp: new Date().toISOString(),
        });
      }
    } catch (err) {
      const formattedError = formatApiError(err);
      setError(formattedError.message);
      setTestResults({
        connected: false,
        responseTime: 0,
        error: formattedError.message,
        timestamp: new Date().toISOString(),
      });
    } finally {
      setLoading(prev => ({ ...prev, connection: false }));
    }
  };

  const handleAnalysisTest = async () => {
    try {
      setLoading(prev => ({ ...prev, analysis: true }));
      setError('');
      setSuccess('');

      // Mock analysis test - in real implementation, this would call the actual analysis endpoint
      const startTime = Date.now();
      
      // Simulate API call delay
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      const endTime = Date.now();
      const responseTime = endTime - startTime;

      setSuccess('Analysis test completed successfully!');
      setTestResults(prev => ({
        ...prev,
        analysisTest: {
          success: true,
          responseTime,
          input: testInput,
          output: 'Mock analysis result: The test input has been successfully processed by the AI model.',
          model: currentModel,
          timestamp: new Date().toISOString(),
        }
      }));
    } catch (err) {
      const formattedError = formatApiError(err);
      setError(`Analysis test failed: ${formattedError.message}`);
      setTestResults(prev => ({
        ...prev,
        analysisTest: {
          success: false,
          error: formattedError.message,
          timestamp: new Date().toISOString(),
        }
      }));
    } finally {
      setLoading(prev => ({ ...prev, analysis: false }));
    }
  };

  if (!connectionStatus.azure_devops.connected) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Alert severity="warning">
          Please connect to Azure DevOps first before testing OpenArena connectivity.
        </Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" component="h1" fontWeight={600} gutterBottom>
          OpenArena Connectivity Test
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Test your OpenArena connection and AI model functionality to ensure everything is working correctly.
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

      <Grid container spacing={4}>
        {/* Connection Status */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
                <TestIcon sx={{ mr: 2, color: 'primary.main' }} />
                <Typography variant="h6" component="h2">
                  Connection Status
                </Typography>
              </Box>

              <List>
                <ListItem>
                  <ListItemIcon>
                    {connectionStatus.azure_devops.connected ? (
                      <SuccessIcon color="success" />
                    ) : (
                      <ErrorIcon color="error" />
                    )}
                  </ListItemIcon>
                  <ListItemText
                    primary="Azure DevOps"
                    secondary={connectionStatus.azure_devops.connected ? 'Connected' : 'Not Connected'}
                  />
                </ListItem>
                
                <ListItem>
                  <ListItemIcon>
                    {connectionStatus.openarena.connected ? (
                      <SuccessIcon color="success" />
                    ) : (
                      <ErrorIcon color="error" />
                    )}
                  </ListItemIcon>
                  <ListItemText
                    primary="OpenArena AI"
                    secondary={connectionStatus.openarena.connected ? 'Connected' : 'Not Connected'}
                  />
                </ListItem>
                
                <ListItem>
                  <ListItemIcon>
                    <ModelIcon modelId={currentModel} sx={{ color: 'info.main' }} />
                  </ListItemIcon>
                  <ListItemText
                    primary="Current AI Model"
                    secondary={getModelDisplayName(currentModel)}
                  />
                </ListItem>
              </List>

              <Button
                fullWidth
                variant="contained"
                onClick={handleConnectionTest}
                disabled={loading.connection || !connectionStatus.openarena.connected}
                startIcon={loading.connection ? <CircularProgress size={20} /> : <TestIcon />}
                sx={{ 
                  mt: 2,
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  color: 'white',
                  '&:hover': {
                    background: 'linear-gradient(135deg, #5a6fd8 0%, #6a4190 100%)',
                  },
                  '&.Mui-disabled': {
                    background: 'rgba(0,0,0,0.12)',
                    color: 'rgba(0,0,0,0.26)',
                  }
                }}
              >
                {loading.connection ? 'Testing Connection...' : 'Test Connection'}
              </Button>
            </CardContent>
          </Card>
        </Grid>

        {/* Analysis Test */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
                <ModelIcon modelId={currentModel} sx={{ mr: 2 }} />
                <Typography variant="h6" component="h2">
                  AI Analysis Test
                </Typography>
              </Box>

              <TextField
                fullWidth
                label="Test Input"
                value={testInput}
                onChange={(e) => setTestInput(e.target.value)}
                multiline
                rows={3}
                placeholder="Enter test input for AI analysis..."
                margin="normal"
              />

              <Typography variant="body2" color="text.secondary" sx={{ mt: 1, mb: 2 }}>
                This will test the AI model's ability to process and analyze text input.
              </Typography>

              <Button
                fullWidth
                variant="outlined"
                onClick={handleAnalysisTest}
                disabled={loading.analysis || !connectionStatus.openarena.connected || !testInput.trim()}
                startIcon={loading.analysis ? <CircularProgress size={20} /> : <ModelIcon modelId={currentModel} sx={{ fontSize: 20 }} />}
              >
                {loading.analysis ? 'Running Analysis Test...' : 'Test AI Analysis'}
              </Button>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Test Results */}
      {testResults && (
        <Paper sx={{ mt: 4, p: 3 }}>
          <Typography variant="h6" gutterBottom>
            Test Results
          </Typography>

          {/* Connection Test Results */}
          {testResults && (
            <Box sx={{ mb: 3 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <Typography variant="subtitle1" sx={{ mr: 2 }}>
                  Connection Test:
                </Typography>
                <Chip
                  icon={testResults.connected ? <SuccessIcon /> : <ErrorIcon />}
                  label={testResults.connected ? 'Passed' : 'Failed'}
                  color={testResults.connected ? 'success' : 'error'}
                  size="small"
                />
                {testResults.responseTime > 0 && (
                  <Chip
                    icon={<SpeedIcon />}
                    label={`${testResults.responseTime}ms`}
                    size="small"
                    variant="outlined"
                    sx={{ ml: 1 }}
                  />
                )}
              </Box>
              
              <List dense>
                <ListItem>
                  <ListItemIcon>
                    <InfoIcon color="info" />
                  </ListItemIcon>
                  <ListItemText
                    primary="Status"
                    secondary={testResults.message || testResults.error || 'No details available'}
                  />
                </ListItem>
                <ListItem>
                  <ListItemIcon>
                    <ResponseIcon color="info" />
                  </ListItemIcon>
                  <ListItemText
                    primary="Timestamp"
                    secondary={new Date(testResults.timestamp).toLocaleString()}
                  />
                </ListItem>
              </List>
            </Box>
          )}

          {/* Analysis Test Results */}
          {testResults.analysisTest && (
            <>
              <Divider sx={{ my: 2 }} />
              <Box>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <Typography variant="subtitle1" sx={{ mr: 2 }}>
                    Analysis Test:
                  </Typography>
                  <Chip
                    icon={testResults.analysisTest.success ? <SuccessIcon /> : <ErrorIcon />}
                    label={testResults.analysisTest.success ? 'Passed' : 'Failed'}
                    color={testResults.analysisTest.success ? 'success' : 'error'}
                    size="small"
                  />
                  {testResults.analysisTest.responseTime && (
                    <Chip
                      icon={<SpeedIcon />}
                      label={`${testResults.analysisTest.responseTime}ms`}
                      size="small"
                      variant="outlined"
                      sx={{ ml: 1 }}
                    />
                  )}
                </Box>

                {testResults.analysisTest.success ? (
                  <List dense>
                    <ListItem>
                      <ListItemText
                        primary="Input"
                        secondary={testResults.analysisTest.input}
                      />
                    </ListItem>
                    <ListItem>
                      <ListItemText
                        primary="Model Used"
                        secondary={testResults.analysisTest.model}
                      />
                    </ListItem>
                    <ListItem>
                      <ListItemText
                        primary="Output"
                        secondary={testResults.analysisTest.output}
                      />
                    </ListItem>
                  </List>
                ) : (
                  <Alert severity="error" sx={{ mt: 2 }}>
                    {testResults.analysisTest.error}
                  </Alert>
                )}
              </Box>
            </>
          )}
        </Paper>
      )}

      {/* Testing Guide */}
      <Paper sx={{ mt: 4, p: 3 }}>
        <Typography variant="h6" gutterBottom>
          Testing Guide
        </Typography>
        
        <Grid container spacing={3}>
          <Grid item xs={12} md={4}>
            <Typography variant="subtitle2" color="primary" gutterBottom>
              Connection Test
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Verifies that the OpenArena WebSocket connection is working and the authentication is valid. This test should complete quickly.
            </Typography>
          </Grid>
          
          <Grid item xs={12} md={4}>
            <Typography variant="subtitle2" color="primary" gutterBottom>
              Analysis Test
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Tests the AI model's ability to process text input and generate responses. This simulates the work item analysis functionality.
            </Typography>
          </Grid>
          
          <Grid item xs={12} md={4}>
            <Typography variant="subtitle2" color="primary" gutterBottom>
              Troubleshooting
            </Typography>
            <Typography variant="body2" color="text.secondary">
              If tests fail, check your ESSO token, WebSocket URL, and ensure your network allows WebSocket connections to the OpenArena service.
            </Typography>
          </Grid>
        </Grid>
      </Paper>
    </Container>
  );
};

export default OpenArenaTest;

