import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { Box } from '@mui/material';

// Import components
import Sidebar from './components/Sidebar';
import ConnectionManager from './components/ConnectionManager';
import WorkItemAnalysisTabs from './components/WorkItemAnalysisTabs';
import TeamSelection from './components/TeamSelection';
import ModelSelection from './components/ModelSelection';
import OpenArenaTest from './components/OpenArenaTest';
import { fetchConnectionStatus, performInitialTeamSelection } from './services/api';

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#0078d4', // Azure DevOps blue
      light: '#40a9ff',
      dark: '#0056b3',
    },
    secondary: {
      main: '#ff6b35',
      light: '#ff8a65',
      dark: '#e64a19',
    },
    background: {
      default: '#f8f9fa',
      paper: '#ffffff',
    },
    text: {
      primary: '#323130',
      secondary: '#605e5c',
    },
    success: {
      main: '#107c10',
    },
    warning: {
      main: '#ff8c00',
    },
    error: {
      main: '#d13438',
    },
  },
  typography: {
    fontFamily: '"Segoe UI", "Roboto", "Helvetica", "Arial", sans-serif',
    h1: {
      fontSize: '2.5rem',
      fontWeight: 600,
    },
    h2: {
      fontSize: '2rem',
      fontWeight: 500,
    },
    h3: {
      fontSize: '1.5rem',
      fontWeight: 500,
    },
    h4: {
      fontSize: '1.25rem',
      fontWeight: 500,
    },
    h5: {
      fontSize: '1.1rem',
      fontWeight: 500,
    },
    h6: {
      fontSize: '1rem',
      fontWeight: 500,
    },
  },
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
          borderRadius: '8px',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          borderRadius: '6px',
          fontWeight: 500,
        },
        contained: {
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          color: 'white',
          '&:hover': {
            background: 'linear-gradient(135deg, #5a6fd8 0%, #6a4190 100%)',
          },
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
        },
      },
    },
  },
});


function App() {
  const [connectionStatus, setConnectionStatus] = useState({
    azure_devops: { connected: false },
    openarena: { connected: false }
  });
  const [loading, setLoading] = useState(true);
  const [autoSelectedTeam, setAutoSelectedTeam] = useState(null);

  // Load connection status on app start
  useEffect(() => {
    loadConnectionStatus();
  }, []);

  const loadConnectionStatus = async () => {
    try {
      setLoading(true);
      const status = await fetchConnectionStatus();
      setConnectionStatus(status);
      
      // If Azure DevOps is connected, perform auto team selection
      if (status.azure_devops.connected) {
        console.log('🔗 Azure DevOps connected, starting auto team selection...');
        // Run auto team selection in the background (don't wait for it)
        performInitialTeamSelection().then(result => {
          if (result) {
            console.log('🎯 Auto team selection completed:', result);
            setAutoSelectedTeam(result);
          }
        }).catch(error => {
          console.warn('⚠️ Auto team selection failed:', error);
        });
      }
    } catch (error) {
      console.error('Error loading connection status:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleConnectionUpdate = (newStatus) => {
    setConnectionStatus(newStatus);
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router>
        <Box sx={{ minHeight: '100vh' }}>
          {/* Fixed Sidebar Navigation */}
          <Sidebar connectionStatus={connectionStatus} />

          {/* Main Content Area */}
          <Box
            component="main"
            sx={{
              marginLeft: '320px', // Match the sidebar width
              bgcolor: 'background.default',
              minHeight: '100vh',
              overflow: 'auto',
            }}
          >
            <Routes>
              {/* Default route - always redirect to AI-Powered Item Discovery */}
              <Route 
                path="/" 
                element={
                  <Navigate 
                    to="/work-items-tabs" 
                    replace 
                  />
                } 
              />
              
              {/* Connection Management */}
              <Route 
                path="/connections" 
                element={
                  <ConnectionManager 
                    connectionStatus={connectionStatus}
                    onConnectionUpdate={handleConnectionUpdate}
                  />
                } 
              />
              
              {/* Team Selection */}
              <Route 
                path="/teams" 
                element={
                  <TeamSelection 
                    connectionStatus={connectionStatus}
                  />
                } 
              />
              
              {/* Intelligent AI Model Selection */}
              <Route 
                path="/models" 
                element={
                  <ModelSelection 
                    connectionStatus={connectionStatus}
                  />
                } 
              />
              
              {/* OpenArena Health Check */}
              <Route 
                path="/openarena-test" 
                element={
                  <OpenArenaTest 
                    connectionStatus={connectionStatus}
                  />
                } 
              />
              
              {/* Work Items List - Redirect to new tabbed interface */}
              <Route 
                path="/work-items" 
                element={
                  <Navigate to="/work-items-tabs" replace />
                } 
              />
              
              {/* Work Item Analysis Tabs - New Modern Interface */}
              <Route 
                path="/work-items-tabs" 
                element={
                  <WorkItemAnalysisTabs 
                    connectionStatus={connectionStatus}
                    autoSelectedTeam={autoSelectedTeam}
                  />
                } 
              />
              
              {/* Work Item Analysis - Redirect to new tabbed interface */}
              <Route 
                path="/analysis/:workItemId" 
                element={
                  <Navigate to="/work-items-tabs" replace />
                } 
              />
              
              {/* Legacy analysis route for compatibility */}
              <Route 
                path="/analysis" 
                element={
                  <Navigate to="/work-items-tabs" replace />
                } 
              />
            </Routes>
          </Box>
        </Box>
      </Router>
    </ThemeProvider>
  );
}

export default App;