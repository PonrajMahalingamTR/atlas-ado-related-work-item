import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Paper,
  Typography,
  TextField,
  Button,
  Grid,
  Card,
  CardContent,
  CardActions,
  Alert,
  CircularProgress,
  Divider,
  Chip,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  CheckCircle as ConnectedIcon,
  Error as DisconnectedIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
  Refresh as RefreshIcon,
  Save as SaveIcon,
  Science as TestIcon,
} from '@mui/icons-material';

import {
  fetchConnectionStatus,
  connectAzureDevOps,
  connectOpenArena,
  testOpenArenaConnection,
  fetchConfig,
  saveConfig,
  connectServices,
} from '../services/api';

const ConnectionManager = ({ connectionStatus, onConnectionUpdate }) => {
  const [loading, setLoading] = useState({
    azureDevOps: false,
    openArena: false,
    testing: false,
    config: false,
    autoConnect: false,
  });
  
  const [error, setError] = useState({
    azureDevOps: '',
    openArena: '',
    config: '',
  });
  
  const [success, setSuccess] = useState({
    azureDevOps: '',
    openArena: '',
    config: '',
  });

  const [showTokens, setShowTokens] = useState({
    pat: false,
    esso: false,
  });

  // Azure DevOps form state
  const [azureDevOpsForm, setAzureDevOpsForm] = useState({
    org_url: '',
    pat: '',
    project: '',
  });

  // OpenArena form state
  const [openArenaForm, setOpenArenaForm] = useState({
    esso_token: '',
    websocket_url: '',
    workflow_id: '',
  });

  // Configuration state
  const [configLoaded, setConfigLoaded] = useState(false);
  const [autoConnect, setAutoConnect] = useState(false);

  useEffect(() => {
    // Load configuration on component mount
    loadConfiguration();
  }, []);

  useEffect(() => {
    // Auto-connect if configuration is loaded and auto_connect is enabled
    if (configLoaded && autoConnect && !connectionStatus.azure_devops?.connected) {
      handleAutoConnect();
    }
  }, [configLoaded, autoConnect]);

  const loadConfiguration = async () => {
    try {
      setLoading(prev => ({ ...prev, config: true }));
      setError(prev => ({ ...prev, config: '' }));
      
      const config = await fetchConfig();
      
      // Prepopulate Azure DevOps form
      if (config.azure_devops) {
        setAzureDevOpsForm({
          org_url: config.azure_devops.org_url || '',
          pat: config.azure_devops.pat || '',
          project: config.azure_devops.project || '',
        });
      }
      
      // Prepopulate OpenArena form
      if (config.openarena) {
        setOpenArenaForm({
          esso_token: config.openarena.esso_token || '',
          websocket_url: config.openarena.websocket_url || '',
          workflow_id: config.openarena.workflow_id || '',
        });
      }
      
      // Set auto-connect flag
      setAutoConnect(config.auto_connect || false);
      setConfigLoaded(true);
      
      setSuccess(prev => ({ ...prev, config: 'Configuration loaded successfully' }));
      setTimeout(() => setSuccess(prev => ({ ...prev, config: '' })), 3000);
      
    } catch (err) {
      console.error('Error loading configuration:', err);
      setError(prev => ({ ...prev, config: `Failed to load configuration: ${err.message}` }));
      setConfigLoaded(true); // Still set to true to prevent infinite loading
    } finally {
      setLoading(prev => ({ ...prev, config: false }));
    }
  };

  const handleAutoConnect = async () => {
    try {
      setLoading(prev => ({ ...prev, autoConnect: true }));
      setError(prev => ({ ...prev, azureDevOps: '', openArena: '' }));
      
      // Auto-connect with prepopulated credentials
      const credentials = {};
      
      if (azureDevOpsForm.org_url && azureDevOpsForm.pat) {
        credentials.azure_devops = azureDevOpsForm;
      }
      
      if (openArenaForm.esso_token && openArenaForm.websocket_url && openArenaForm.workflow_id) {
        credentials.openarena = openArenaForm;
      }
      
      const results = await connectServices(credentials);
      
      if (results.success) {
        if (results.connections.azure_devops?.success) {
          setSuccess(prev => ({ ...prev, azureDevOps: 'Auto-connected to Azure DevOps' }));
        }
        if (results.connections.openarena?.success) {
          setSuccess(prev => ({ ...prev, openArena: 'Auto-connected to OpenArena' }));
        }
        
        // Update connection status
        const newStatus = await fetchConnectionStatus();
        onConnectionUpdate(newStatus);
        
        // Clear success messages after 5 seconds
        setTimeout(() => {
          setSuccess({ azureDevOps: '', openArena: '', config: '' });
        }, 5000);
      } else {
        if (results.connections.azure_devops && !results.connections.azure_devops.success) {
          setError(prev => ({ ...prev, azureDevOps: results.connections.azure_devops.message }));
        }
        if (results.connections.openarena && !results.connections.openarena.success) {
          setError(prev => ({ ...prev, openArena: results.connections.openarena.message }));
        }
      }
      
    } catch (err) {
      console.error('Error during auto-connect:', err);
      setError(prev => ({ ...prev, azureDevOps: `Auto-connect failed: ${err.message}` }));
    } finally {
      setLoading(prev => ({ ...prev, autoConnect: false }));
    }
  };

  const handleAzureDevOpsSubmit = async (e) => {
    e.preventDefault();
    setLoading(prev => ({ ...prev, azureDevOps: true }));
    setError(prev => ({ ...prev, azureDevOps: '' }));
    setSuccess(prev => ({ ...prev, azureDevOps: '' }));

    try {
      // First, save the configuration
      await saveConfig({ 
        azure_devops: azureDevOpsForm,
        auto_connect: autoConnect 
      });
      
      // Then connect with the new credentials
      const response = await connectServices({ azure_devops: azureDevOpsForm });
      
      if (response.success && response.connections.azure_devops?.success) {
        setSuccess(prev => ({ ...prev, azureDevOps: 'Connected to Azure DevOps and configuration saved' }));
        
        // Update connection status
        const newStatus = await fetchConnectionStatus();
        onConnectionUpdate(newStatus);
      } else {
        const errorMsg = response.connections?.azure_devops?.message || 'Connection failed';
        setError(prev => ({ ...prev, azureDevOps: errorMsg }));
      }
    } catch (err) {
      setError(prev => ({ ...prev, azureDevOps: err.message }));
    } finally {
      setLoading(prev => ({ ...prev, azureDevOps: false }));
    }
  };

  const handleOpenArenaSubmit = async (e) => {
    e.preventDefault();
    setLoading(prev => ({ ...prev, openArena: true }));
    setError(prev => ({ ...prev, openArena: '' }));
    setSuccess(prev => ({ ...prev, openArena: '' }));

    try {
      // First, save the configuration
      await saveConfig({ 
        openarena: openArenaForm,
        auto_connect: autoConnect 
      });
      
      // Then connect with the new credentials
      const response = await connectServices({ openarena: openArenaForm });
      
      if (response.success && response.connections.openarena?.success) {
        setSuccess(prev => ({ ...prev, openArena: 'Connected to OpenArena and configuration saved' }));
        
        // Update connection status
        const newStatus = await fetchConnectionStatus();
        onConnectionUpdate(newStatus);
      } else {
        const errorMsg = response.connections?.openarena?.message || 'Connection failed';
        setError(prev => ({ ...prev, openArena: errorMsg }));
      }
    } catch (err) {
      setError(prev => ({ ...prev, openArena: err.message }));
    } finally {
      setLoading(prev => ({ ...prev, openArena: false }));
    }
  };

  const handleTestOpenArena = async () => {
    setLoading(prev => ({ ...prev, testing: true }));
    setError(prev => ({ ...prev, openArena: '' }));
    setSuccess(prev => ({ ...prev, openArena: '' }));

    try {
      const response = await testOpenArenaConnection();
      
      if (response.connected) {
        setSuccess(prev => ({ ...prev, openArena: response.message }));
      } else {
        setError(prev => ({ ...prev, openArena: response.message || 'Connection test failed' }));
      }
    } catch (err) {
      setError(prev => ({ ...prev, openArena: err.message }));
    } finally {
      setLoading(prev => ({ ...prev, testing: false }));
    }
  };

  const handleRefreshStatus = async () => {
    try {
      const newStatus = await fetchConnectionStatus();
      onConnectionUpdate(newStatus);
    } catch (err) {
      console.error('Error refreshing status:', err);
    }
  };

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h4" component="h1" fontWeight={600}>
            Connection Management
          </Typography>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={handleRefreshStatus}
            size="small"
          >
            Refresh Status
          </Button>
        </Box>
        <Typography variant="body1" color="text.secondary">
          Configure your Azure DevOps and OpenArena connections to enable all application features.
        </Typography>
      </Box>

      {/* Configuration Loading Status */}
      {loading.config && (
        <Alert severity="info" sx={{ mb: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <CircularProgress size={16} sx={{ mr: 1 }} />
            Loading configuration...
          </Box>
        </Alert>
      )}

      {/* Auto-connect Status */}
      {loading.autoConnect && (
        <Alert severity="info" sx={{ mb: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <CircularProgress size={16} sx={{ mr: 1 }} />
            Auto-connecting to services...
          </Box>
        </Alert>
      )}

      {/* Configuration Success */}
      {success.config && (
        <Alert severity="success" sx={{ mb: 2 }}>
          {success.config}
        </Alert>
      )}

      {/* Configuration Error */}
      {error.config && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error.config}
        </Alert>
      )}

      {/* Auto-connect Notice */}
      {configLoaded && autoConnect && (
        <Alert severity="info" sx={{ mb: 2 }}>
          Auto-connect is enabled. The system will automatically connect using saved configuration values.
        </Alert>
      )}

      <Grid container spacing={4}>
        {/* Azure DevOps Connection */}
        <Grid item xs={12} lg={6}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
                <Typography variant="h6" component="h2" sx={{ flexGrow: 1 }}>
                  Azure DevOps Connection
                </Typography>
                <Chip
                  icon={connectionStatus.azure_devops.connected ? <ConnectedIcon /> : <DisconnectedIcon />}
                  label={connectionStatus.azure_devops.connected ? 'Connected' : 'Disconnected'}
                  color={connectionStatus.azure_devops.connected ? 'success' : 'error'}
                  size="small"
                />
              </Box>

              {success.azureDevOps && (
                <Alert severity="success" sx={{ mb: 2 }}>
                  {success.azureDevOps}
                </Alert>
              )}

              {error.azureDevOps && (
                <Alert severity="error" sx={{ mb: 2 }}>
                  {error.azureDevOps}
                </Alert>
              )}

              <Box component="form" onSubmit={handleAzureDevOpsSubmit}>
                <TextField
                  fullWidth
                  label="Organization URL"
                  value={azureDevOpsForm.org_url}
                  onChange={(e) => setAzureDevOpsForm(prev => ({ ...prev, org_url: e.target.value }))}
                  placeholder="https://dev.azure.com/yourorg"
                  margin="normal"
                  required
                />

                <TextField
                  fullWidth
                  label="Personal Access Token (PAT)"
                  type={showTokens.pat ? 'text' : 'password'}
                  value={azureDevOpsForm.pat}
                  onChange={(e) => setAzureDevOpsForm(prev => ({ ...prev, pat: e.target.value }))}
                  placeholder="Your Azure DevOps PAT"
                  margin="normal"
                  required
                  InputProps={{
                    endAdornment: (
                      <IconButton
                        onClick={() => setShowTokens(prev => ({ ...prev, pat: !prev.pat }))}
                        edge="end"
                      >
                        {showTokens.pat ? <VisibilityOffIcon /> : <VisibilityIcon />}
                      </IconButton>
                    ),
                  }}
                />

                <TextField
                  fullWidth
                  label="Project Name"
                  value={azureDevOpsForm.project}
                  onChange={(e) => setAzureDevOpsForm(prev => ({ ...prev, project: e.target.value }))}
                  placeholder="Your project name (optional)"
                  margin="normal"
                />

                <Button
                  type="submit"
                  variant="contained"
                  fullWidth
                  disabled={loading.azureDevOps}
                  startIcon={loading.azureDevOps ? <CircularProgress size={20} /> : <SaveIcon />}
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
                  {loading.azureDevOps ? 'Connecting...' : 'Connect to Azure DevOps'}
                </Button>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* OpenArena Connection */}
        <Grid item xs={12} lg={6}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
                <Typography variant="h6" component="h2" sx={{ flexGrow: 1 }}>
                  OpenArena AI Connection
                </Typography>
                <Chip
                  icon={connectionStatus.openarena.connected ? <ConnectedIcon /> : <DisconnectedIcon />}
                  label={connectionStatus.openarena.connected ? 'Connected' : 'Disconnected'}
                  color={connectionStatus.openarena.connected ? 'success' : 'warning'}
                  size="small"
                />
              </Box>

              {success.openArena && (
                <Alert severity="success" sx={{ mb: 2 }}>
                  {success.openArena}
                </Alert>
              )}

              {error.openArena && (
                <Alert severity="error" sx={{ mb: 2 }}>
                  {error.openArena}
                </Alert>
              )}

              <Box component="form" onSubmit={handleOpenArenaSubmit}>
                <TextField
                  fullWidth
                  label="ESSO Token"
                  type={showTokens.esso ? 'text' : 'password'}
                  value={openArenaForm.esso_token}
                  onChange={(e) => setOpenArenaForm(prev => ({ ...prev, esso_token: e.target.value }))}
                  placeholder="Your ESSO authentication token"
                  margin="normal"
                  InputProps={{
                    endAdornment: (
                      <IconButton
                        onClick={() => setShowTokens(prev => ({ ...prev, esso: !prev.esso }))}
                        edge="end"
                      >
                        {showTokens.esso ? <VisibilityOffIcon /> : <VisibilityIcon />}
                      </IconButton>
                    ),
                  }}
                />

                <TextField
                  fullWidth
                  label="WebSocket URL"
                  value={openArenaForm.websocket_url}
                  onChange={(e) => setOpenArenaForm(prev => ({ ...prev, websocket_url: e.target.value }))}
                  placeholder="WebSocket service URL"
                  margin="normal"
                />

                <TextField
                  fullWidth
                  label="Workflow ID"
                  value={openArenaForm.workflow_id}
                  onChange={(e) => setOpenArenaForm(prev => ({ ...prev, workflow_id: e.target.value }))}
                  placeholder="GPT-4o workflow ID"
                  margin="normal"
                />

                <Box sx={{ display: 'flex', gap: 1, mt: 2 }}>
                  <Button
                    type="submit"
                    variant="contained"
                    disabled={loading.openArena}
                    startIcon={loading.openArena ? <CircularProgress size={20} /> : <SaveIcon />}
                    sx={{ 
                      flexGrow: 1,
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
                    {loading.openArena ? 'Connecting...' : 'Save Settings'}
                  </Button>
                  
                  <Tooltip title="Test OpenArena Connection">
                    <Button
                      variant="outlined"
                      onClick={handleTestOpenArena}
                      disabled={loading.testing}
                      startIcon={loading.testing ? <CircularProgress size={20} /> : <TestIcon />}
                    >
                      Test
                    </Button>
                  </Tooltip>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Connection Guide */}
      <Paper sx={{ mt: 4, p: 3 }}>
        <Typography variant="h6" component="h3" gutterBottom>
          Connection Setup Guide
        </Typography>
        
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Typography variant="subtitle2" gutterBottom>
              Azure DevOps Setup:
            </Typography>
            <Typography variant="body2" color="text.secondary" component="div">
              <ol style={{ paddingLeft: '20px' }}>
                <li>Go to Azure DevOps → User Settings → Personal Access Tokens</li>
                <li>Create a new token with "Work items (read)" permission</li>
                <li>Copy the token and enter it above</li>
                <li>Enter your organization URL (e.g., https://dev.azure.com/yourorg)</li>
              </ol>
            </Typography>
          </Grid>
          
          <Grid item xs={12} md={6}>
            <Typography variant="subtitle2" gutterBottom>
              OpenArena Setup:
            </Typography>
            <Typography variant="body2" color="text.secondary" component="div">
              <ol style={{ paddingLeft: '20px' }}>
                <li>Get your ESSO token from Thomson Reuters OpenArena</li>
                <li>Enter the WebSocket URL provided by your admin</li>
                <li>Specify the workflow ID for the OpenArena Chain's AI Model</li>
                <li>Click "Test" to verify the connection</li>
              </ol>
            </Typography>
          </Grid>
        </Grid>
      </Paper>
    </Container>
  );
};

export default ConnectionManager;

