import React from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import {
  Box,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Typography,
  Chip,
  Avatar,
  Divider,
  Button,
} from '@mui/material';
import {
  Settings as SettingsIcon,
  Group as TeamIcon,
  Psychology as ModelIcon,
  Science as TestIcon,
  ViewList as WorkItemsIcon,
  Analytics as AnalysisIcon,
  CheckCircle as ConnectedIcon,
  Error as DisconnectedIcon,
  CloudSync as DevOpsIcon,
} from '@mui/icons-material';

const Sidebar = ({ connectionStatus }) => {
  const navigate = useNavigate();
  const location = useLocation();

  const navigationItems = [
    {
      id: 'work-items',
      label: 'AI-Powered Item Discovery',
      icon: <WorkItemsIcon />,
      path: '/work-items-tabs',
      description: 'Find related work items with AI',
      requiresConnection: true,
    },
    {
      id: 'models',
      label: 'Intelligent AI Model Selection',
      icon: <ModelIcon />,
      path: '/models',
      description: 'Smart AI model recommendations',
      requiresConnection: true,
    },
    {
      id: 'teams',
      label: 'Smart Team Discovery',
      icon: <TeamIcon />,
      path: '/teams',
      description: 'Discover your perfect team',
      requiresConnection: true,
    },
    {
      id: 'connections',
      label: 'Connection Setup',
      icon: <SettingsIcon />,
      path: '/connections',
      description: 'Azure DevOps & OpenArena setup',
    },
  ];

  const handleNavigate = (path, requiresConnection = false) => {
    if (requiresConnection && !connectionStatus.azure_devops.connected) {
      // Redirect to connections page if not connected
      navigate('/connections');
      return;
    }
    navigate(path);
  };

  const isActive = (path) => {
    return location.pathname === path || 
           (path === '/work-items-tabs' && (location.pathname.startsWith('/work-items') || location.pathname.startsWith('/analysis'))) ||
           (path === '/analysis' && location.pathname.startsWith('/analysis'));
  };

  return (
    <Box sx={{ 
      display: 'flex', 
      flexDirection: 'column', 
      height: '100vh',
      position: 'fixed',
      top: 0,
      left: 0,
      width: '320px',
      zIndex: 1000,
      backgroundColor: 'background.paper',
      borderRight: '1px solid',
      borderColor: 'divider'
    }}>
      {/* Application Logo */}
      <Box sx={{ p: 1.5, borderBottom: '1px solid', borderColor: 'divider', textAlign: 'center' }}>
        <Box
          component="img"
          src="/application_logo.png"
          alt="ADO Task Learning And Semantic System Logo"
          sx={{
            maxWidth: '100%',
            maxHeight: 100,
            objectFit: 'contain',
          }}
        />
      </Box>

      {/* Navigation */}
      <Box sx={{ flex: 1, overflow: 'auto' }}>
        <List sx={{ px: 1, py: 2 }}>
          {navigationItems.map((item) => {
            const disabled = item.requiresConnection && !connectionStatus.azure_devops.connected;
            const active = isActive(item.path);

            return (
              <ListItem key={item.id} disablePadding sx={{ mb: 1 }}>
                <ListItemButton
                  onClick={() => handleNavigate(item.path, item.requiresConnection)}
                  disabled={disabled}
                  sx={{
                    borderRadius: 2,
                    py: 1.5,
                    backgroundColor: active ? 'transparent' : 'transparent',
                    background: active ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' : 'transparent',
                    color: active ? 'white' : disabled ? 'text.disabled' : 'text.primary',
                    '&:hover': {
                      backgroundColor: active ? 'transparent' : 'action.hover',
                      background: active ? 'linear-gradient(135deg, #5a6fd8 0%, #6a4190 100%)' : 'transparent',
                    },
                    '&.Mui-disabled': {
                      opacity: 0.5,
                    },
                  }}
                >
                  <ListItemIcon
                    sx={{
                      color: 'inherit',
                      minWidth: 40,
                    }}
                  >
                    {item.icon}
                  </ListItemIcon>
                  <ListItemText
                    primary={item.label}
                    secondary={
                      <Typography 
                        variant="body2" 
                        sx={{ 
                          color: active ? 'primary.contrastText' : 'text.secondary',
                          opacity: active ? 0.8 : 1,
                          fontSize: '0.75rem',
                          wordBreak: 'break-word'
                        }}
                      >
                        {item.description}
                      </Typography>
                    }
                    primaryTypographyProps={{
                      fontSize: '0.9rem',
                      fontWeight: active ? 600 : 500,
                      noWrap: false,
                      sx: { wordBreak: 'break-word' }
                    }}
                  />
                </ListItemButton>
              </ListItem>
            );
          })}
        </List>
      </Box>

      {/* OpenArena Health Check Menu Item - Fixed at bottom */}
      <Box 
        sx={{ 
          position: 'fixed',
          bottom: 0,
          left: 0,
          width: '320px', // Match sidebar width
          backgroundColor: 'background.paper',
          borderTop: '1px solid',
          borderRight: '1px solid',
          borderColor: 'divider',
          px: 1,
          py: 1,
          zIndex: 1000,
        }}
      >
        <ListItem disablePadding sx={{ mb: 1 }}>
          <ListItemButton
            component={Link}
            to="/openarena-test"
            selected={location.pathname === '/openarena-test'}
            sx={{
              borderRadius: 2,
              py: 1.5,
              backgroundColor: location.pathname === '/openarena-test' ? 'transparent' : 'transparent',
              background: location.pathname === '/openarena-test' ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' : 'transparent',
              color: location.pathname === '/openarena-test' ? 'white' : 'text.primary',
              '&:hover': {
                backgroundColor: location.pathname === '/openarena-test' ? 'transparent' : 'action.hover',
                background: location.pathname === '/openarena-test' ? 'linear-gradient(135deg, #5a6fd8 0%, #6a4190 100%)' : 'transparent',
              },
              '&.Mui-selected': {
                background: 'linear-gradient(135deg, #5a6fd8 0%, #6a4190 100%)',
                color: 'white',
                '&:hover': {
                  background: 'linear-gradient(135deg, #4a5bc8 0%, #5a3190 100%)',
                },
                '& .MuiListItemIcon-root': {
                  color: 'white',
                },
                '& .MuiListItemText-primary': {
                  color: 'white',
                },
                '& .MuiListItemText-secondary': {
                  color: 'rgba(255, 255, 255, 0.7)',
                },
              },
            }}
          >
            <ListItemIcon
              sx={{
                color: 'inherit',
                minWidth: 40,
              }}
            >
              <TestIcon />
            </ListItemIcon>
            <ListItemText
              primary="OpenArena Health Check"
              secondary={
                <Typography 
                  variant="body2" 
                  sx={{ 
                    color: location.pathname === '/openarena-test' ? 'primary.contrastText' : 'text.secondary',
                    opacity: location.pathname === '/openarena-test' ? 0.8 : 1,
                    fontSize: '0.75rem',
                    wordBreak: 'break-word'
                  }}
                >
                  Validate AI system status
                </Typography>
              }
              primaryTypographyProps={{
                fontSize: '0.9rem',
                fontWeight: location.pathname === '/openarena-test' ? 600 : 500,
                noWrap: false,
                sx: { wordBreak: 'break-word' }
              }}
            />
          </ListItemButton>
        </ListItem>
      </Box>
    </Box>
  );
};

export default Sidebar;

