import React, { useState, useEffect, useMemo } from 'react';
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
  List,
  ListItem,
  ListItemText,
  Chip,
  Alert,
  CircularProgress,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  InputAdornment,
  Autocomplete,
  Badge,
  Divider,
  Collapse,
} from '@mui/material';
import {
  Group as TeamIcon,
  AccountTree as ProjectIcon,
  CheckCircle as SelectedIcon,
  CheckCircle as CheckCircleIcon,
  RadioButtonUnchecked as UnselectedIcon,
  Search as SearchIcon,
  Clear as ClearIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  FilterList as FilterIcon,
} from '@mui/icons-material';

import {
  fetchProjects,
  fetchTeams,
  fetchTeamsByProject,
  fetchTeamAreaPaths,
  setCurrentTeam,
  formatApiError,
  autoSelectTeam,
  trackAnalyticsEvent,
} from '../services/api';

const TeamSelection = ({ connectionStatus }) => {
  const [loading, setLoading] = useState({
    projects: false,
    teams: false,
    areaPaths: false,
  });
  
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  
  const [projects, setProjects] = useState([]);
  const [teams, setTeams] = useState([]);
  const [areaPaths, setAreaPaths] = useState([]);
  
  const [selectedProject, setSelectedProject] = useState('');
  const [selectedTeam, setSelectedTeam] = useState(null);
  
  // New UI state
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedTeamGroup, setSelectedTeamGroup] = useState('all');
  const [showAdvancedSearch, setShowAdvancedSearch] = useState(false);
  
  // Auto-selection state
  const [autoSelecting, setAutoSelecting] = useState(false);
  const [autoSelectionResult, setAutoSelectionResult] = useState(null);
  const [showSelectionReason, setShowSelectionReason] = useState(false);

  useEffect(() => {
    if (connectionStatus.azure_devops.connected) {
      loadProjects();
      loadTeams(); // Load default teams on initial connection
      
      // Set default project if available from connection status
      if (connectionStatus.azure_devops.project && !selectedProject) {
        // Find project by name from connection status
        const defaultProjectName = connectionStatus.azure_devops.project;
        console.log(`Setting default project from connection: ${defaultProjectName}`);
        // We'll set the selectedProject after projects are loaded
      }
    }
  }, [connectionStatus.azure_devops.connected]);

  // Set default project after projects are loaded
  useEffect(() => {
    if (projects.length > 0 && !selectedProject && connectionStatus.azure_devops.project) {
      const defaultProject = projects.find(p => p.name === connectionStatus.azure_devops.project);
      if (defaultProject) {
        console.log(`Auto-selecting default project: ${defaultProject.name}`);
        setSelectedProject(defaultProject.id);
      }
    }
  }, [projects, selectedProject, connectionStatus.azure_devops.project]);

  // Load teams when project selection changes
  useEffect(() => {
    if (selectedProject && connectionStatus.azure_devops.connected) {
      const selectedProjectData = projects.find(p => p.id === selectedProject);
      if (selectedProjectData) {
        loadTeamsForProject(selectedProjectData.name);
      }
    }
  }, [selectedProject, projects, connectionStatus.azure_devops.connected]);

  // Auto-select team when teams are loaded and no team is selected
  useEffect(() => {
    if (teams.length > 0 && !selectedTeam && connectionStatus.azure_devops.connected) {
      performAutoSelection();
    }
  }, [teams, selectedTeam, connectionStatus.azure_devops.connected]);

  const loadProjects = async () => {
    try {
      setLoading(prev => ({ ...prev, projects: true }));
      const projectsData = await fetchProjects();
      setProjects(projectsData || []);
    } catch (err) {
      const formattedError = formatApiError(err);
      console.log('Projects error - Formatted error from API:', formattedError);
      console.log('Projects error - Error state value before setting:', formattedError.message);
      setError(formattedError.message);
    } finally {
      setLoading(prev => ({ ...prev, projects: false }));
    }
  };

  const loadTeams = async () => {
    try {
      setLoading(prev => ({ ...prev, teams: true }));
      const response = await fetchTeams(); // Default teams (fallback to session config)
      const teamsData = response?.teams || response || [];
      setTeams(teamsData);
    } catch (err) {
      const formattedError = formatApiError(err);
      console.log('Teams error - Formatted error from API:', formattedError);
      console.log('Teams error - Error state value before setting:', formattedError.message);
      setError(formattedError.message);
    } finally {
      setLoading(prev => ({ ...prev, teams: false }));
    }
  };

  const loadTeamsForProject = async (projectName) => {
    try {
      setLoading(prev => ({ ...prev, teams: true }));
      setError(''); // Clear any previous errors
      setSelectedTeam(null); // Clear selected team when project changes
      setAreaPaths([]); // Clear area paths when project changes
      
      console.log(`Loading teams for project: ${projectName}`);
      const response = await fetchTeamsByProject(projectName);
      
      // Handle new response structure with teams array and counts
      const teamsData = response.teams || response || [];
      setTeams(teamsData);
      
      if (teamsData && teamsData.length > 0) {
        const verifiedCount = response.verified_count || 0;
        const totalCount = response.total_count || teamsData.length;
        
        
        setSuccess(`Loaded ${teamsData.length} teams for project: ${projectName} (${verifiedCount} verified, ${totalCount} total)`);
        // Clear success message after 5 seconds
        setTimeout(() => setSuccess(''), 5000);
      }
    } catch (err) {
      const formattedError = formatApiError(err);
      console.log('Teams for project error - Formatted error from API:', formattedError);
      console.log('Teams for project error - Error state value before setting:', formattedError.message);
      setError(`Error loading teams for ${projectName}: ${formattedError.message}`);
      setTeams([]); // Clear teams on error
    } finally {
      setLoading(prev => ({ ...prev, teams: false }));
    }
  };

  const loadAreaPaths = async (teamId) => {
    try {
      setLoading(prev => ({ ...prev, areaPaths: true }));
      const areaPathsData = await fetchTeamAreaPaths(teamId);
      setAreaPaths(areaPathsData || []);
    } catch (err) {
      const formattedError = formatApiError(err);
      console.log('Area paths error - Formatted error from API:', formattedError);
      console.log('Area paths error - Error state value before setting:', formattedError.message);
      setError(formattedError.message);
      setAreaPaths([]);
    } finally {
      setLoading(prev => ({ ...prev, areaPaths: false }));
    }
  };

  const performAutoSelection = async () => {
    if (!selectedProject || teams.length === 0) return;
    
    setAutoSelecting(true);
    setError('');
    
    try {
      const selectedProjectData = projects.find(p => p.id === selectedProject);
      if (!selectedProjectData) {
        throw new Error('Selected project not found');
      }

      console.log('🤖 Starting automatic team selection...');
      
      const result = await autoSelectTeam(selectedProjectData.name, 'current_user');
      console.log('🎯 Auto-selection result:', result);

      if (result.selectedTeam && result.selectedTeam.id) {
        // Find the team in our teams list
        const selectedTeamData = teams.find(team => team.id === result.selectedTeam.id);
        
        if (selectedTeamData) {
          setSelectedTeam(selectedTeamData);
          setAutoSelectionResult(result);
          setSuccess(`🎯 Auto-selected: ${result.selectedTeam.name} (${Math.round(result.selectedTeam.confidence * 100)}% confidence)`);
          
          // Track successful auto-selection
          trackSelectionEvent(result, 'accepted');
          
          // Clear success message after 5 seconds
          setTimeout(() => setSuccess(''), 5000);
        } else {
          throw new Error(`Selected team ${result.selectedTeam.name} not found in teams list`);
        }
      } else {
        throw new Error('No team was selected by the auto-selection algorithm');
      }
      
    } catch (err) {
      console.error('Auto-selection error:', err);
      setError(`Auto-selection failed: ${err.message}. Please select a team manually.`);
      
      // Track failed auto-selection
      trackSelectionEvent(null, 'failed', err.message);
    } finally {
      setAutoSelecting(false);
    }
  };

  const handleAutoSelect = async () => {
    await performAutoSelection();
  };

  const trackSelectionEvent = async (selectionResult, userAction, errorMessage = null) => {
    try {
      const eventData = {
        eventType: userAction, // 'auto_selected', 'manual_override', 'selection_failed'
        teamId: selectionResult?.selectedTeam?.id || null,
        teamName: selectionResult?.selectedTeam?.name || null,
        confidence: selectionResult?.selectedTeam?.confidence || null,
        reason: selectionResult?.selectedTeam?.reasons?.join(', ') || errorMessage,
        timestamp: new Date().toISOString(),
        projectId: selectedProject,
        totalTeams: teams.length,
        filteredTeams: filteredTeams.length
      };

      // Send analytics event to backend
      await trackAnalyticsEvent(eventData);
      console.log('📊 Team selection event tracked:', eventData);
    } catch (error) {
      console.warn('Error tracking selection event:', error);
    }
  };

  const formatSelectionReason = (reason) => {
    const reasonMap = {
      'user_profile_preference': 'User Profile Preference',
      'highest_workitem_activity': 'Highest Work Item Activity',
      'project_default_fallback': 'Project Default (Fallback)'
    };
    return reasonMap[reason] || reason;
  };

  // Smart team filtering and grouping
  const { filteredTeams, teamGroups } = useMemo(() => {
    if (!teams || teams.length === 0) {
      return { filteredTeams: [], teamGroups: [] };
    }

    // Filter teams based on search term
    let filtered = Array.isArray(teams) ? teams : [];
    if (searchTerm) {
      const searchLower = searchTerm.toLowerCase();
      filtered = filtered.filter(team => 
        team.name.toLowerCase().includes(searchLower) ||
        (team.description && team.description.toLowerCase().includes(searchLower))
      );
    }

    // Create team groups for better organization
    const groups = {};
    if (Array.isArray(filtered)) {
      filtered.forEach(team => {
      // Extract team prefix/category (e.g., "Labs", "UX", "TR-RST", etc.)
      let groupKey = 'Other';
      const name = team.name;
      
      if (name.includes('Labs')) groupKey = 'Labs Teams';
      else if (name.includes('UX') || name.includes('Reporting Team')) groupKey = 'UX/Reporting Teams';
      else if (name.startsWith('TR-RST')) groupKey = 'TR-RST Teams';
      else if (name.includes('Westlaw') || name.startsWith('WL')) groupKey = 'Westlaw Teams';
      else if (name.includes('Accessibility')) groupKey = 'Accessibility Teams';
      else if (name.includes('Practical Law') || name.includes('PracticalLaw')) groupKey = 'Practical Law Teams';
      else if (name.includes('Editorial')) groupKey = 'Editorial Teams';
      
      if (!groups[groupKey]) groups[groupKey] = [];
      groups[groupKey].push(team);
      });
    }

    // Sort teams within each group
    Object.keys(groups).forEach(key => {
      groups[key].sort((a, b) => a.name.localeCompare(b.name));
    });

    // Filter by selected group
    let finalFiltered = filtered;
    if (selectedTeamGroup !== 'all') {
      finalFiltered = groups[selectedTeamGroup] || [];
    }

    return {
      filteredTeams: finalFiltered,
      teamGroups: Object.keys(groups).sort()
    };
  }, [teams, searchTerm, selectedTeamGroup]);

  const handleTeamSelect = async (team) => {
    try {
      setError('');
      setSuccess('');
      
      // Set as selected team
      setSelectedTeam(team);
      
      // Load area paths for this team
      await loadAreaPaths(team.id);
      
      // Set current team in backend
      await setCurrentTeam({
        team_id: team.id,
        team_name: team.name,
      });
      
      setSuccess(`Selected team: ${team.name}`);
    } catch (err) {
      const formattedError = formatApiError(err);
      console.log('Auto selection error - Formatted error from API:', formattedError);
      console.log('Auto selection error - Error state value before setting:', formattedError.message);
      setError(formattedError.message);
    }
  };

  if (!connectionStatus.azure_devops.connected) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Alert severity="warning">
          Please connect to Azure DevOps first to select teams and projects.
        </Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="xl" sx={{ py: 3 }}>
      {/* Header Section - Compact */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" component="h1" fontWeight={600} gutterBottom>
          Smart Team Discovery
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Discover and select the perfect team for your Azure DevOps project with intelligent recommendations.
        </Typography>
      </Box>

      {/* Error and Success Messages */}
      {error && !error.includes('Team information is being loaded') && error !== 'Team information is being loaded...' && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess('')}>
          {success}
        </Alert>
      )}

      {/* Modern Compact Selection Panel */}
      <Card sx={{ 
        mb: 2, 
        background: 'linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%)',
        border: '1px solid #e2e8f0',
        boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)'
      }}>
        <CardContent sx={{ p: 3 }}>
          {/* Header with Status Indicators */}
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <Box sx={{ 
                p: 1.5, 
                bgcolor: 'primary.main', 
                borderRadius: 2, 
                mr: 2,
                boxShadow: '0 2px 4px rgba(25, 118, 210, 0.2)'
              }}>
                <ProjectIcon sx={{ color: 'white', fontSize: 20 }} />
              </Box>
              <Box>
                <Typography variant="h6" sx={{ fontWeight: 700, color: 'text.primary', mb: 0.5 }}>
                  Smart Team Discovery
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Discover the perfect team with AI-powered recommendations
                </Typography>
              </Box>
            </Box>
            
            {/* Status Badges */}
            <Box sx={{ display: 'flex', gap: 1 }}>
              {selectedProject && (
                <Chip 
                  icon={<CheckCircleIcon sx={{ fontSize: 16 }} />}
                  label="Project Selected" 
                  color="primary" 
                  variant="filled"
                  size="small"
                  sx={{ fontWeight: 600 }}
                />
              )}
              {selectedTeam && (
                <Chip 
                  icon={<CheckCircleIcon sx={{ fontSize: 16 }} />}
                  label="Team Selected" 
                  color="success" 
                  variant="filled"
                  size="small"
                  sx={{ fontWeight: 600 }}
                />
              )}
            </Box>
          </Box>

          {/* Main Content Grid */}
          <Grid container spacing={3}>
            {/* Project Selection */}
            <Grid item xs={12} md={6}>
              <Box sx={{ 
                p: 2.5, 
                bgcolor: 'white', 
                borderRadius: 2, 
                border: '1px solid #e2e8f0',
                boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
                height: '100%'
              }}>
                <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2, color: 'text.primary' }}>
                  Select Project
                </Typography>
                
                {loading.projects ? (
                  <Box sx={{ display: 'flex', alignItems: 'center', py: 2 }}>
                    <CircularProgress size={20} sx={{ mr: 1 }} />
                    <Typography variant="body2" color="text.secondary">Loading projects...</Typography>
                  </Box>
                ) : (
                  <FormControl fullWidth>
                    <InputLabel>Choose Project</InputLabel>
                    <Select
                      value={selectedProject}
                      onChange={(e) => {
                        const newProject = e.target.value;
                        console.log(`Project selected: ${newProject}`);
                        setSelectedProject(newProject);
                      }}
                      label="Choose Project"
                    >
                      {projects.map((project) => (
                        <MenuItem key={project.id} value={project.id}>
                          {project.name}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                )}

                {selectedProject && !selectedTeam && (
                  <Box sx={{ mt: 2 }}>
                    <Button
                      fullWidth
                      variant="contained"
                      onClick={handleAutoSelect}
                      disabled={autoSelecting}
                      startIcon={autoSelecting ? <CircularProgress size={16} /> : <TeamIcon />}
                      sx={{ 
                        background: 'linear-gradient(45deg, #10b981 30%, #059669 90%)',
                        borderRadius: 2,
                        py: 1.5,
                        fontWeight: 600,
                        textTransform: 'none',
                        boxShadow: '0 2px 4px rgba(16, 185, 129, 0.3)',
                        '&:hover': {
                          background: 'linear-gradient(45deg, #059669 30%, #047857 90%)',
                          boxShadow: '0 4px 8px rgba(16, 185, 129, 0.4)',
                        }
                      }}
                    >
                      {autoSelecting ? 'Auto-Selecting Team...' : '🤖 Auto-Select Team'}
                    </Button>
                  </Box>
                )}
              </Box>
            </Grid>

            {/* Current Selection Display */}
            <Grid item xs={12} md={6}>
              <Box sx={{ 
                p: 2.5, 
                bgcolor: 'white', 
                borderRadius: 2, 
                border: '1px solid #e2e8f0',
                boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
                height: '100%'
              }}>
                <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2, color: 'text.primary' }}>
                  Current Selection
                </Typography>
                
                {selectedProject || selectedTeam ? (
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                    {/* Selected Project */}
                    {selectedProject && (
                      <Box sx={{ 
                        p: 2, 
                        bgcolor: 'primary.50', 
                        borderRadius: 1.5,
                        border: '1px solid #bfdbfe',
                        borderLeft: '4px solid #3b82f6'
                      }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                          <Box sx={{ 
                            width: 8, 
                            height: 8, 
                            bgcolor: 'primary.main', 
                            borderRadius: '50%', 
                            mr: 1 
                          }} />
                          <Typography variant="caption" sx={{ fontWeight: 600, color: 'primary.main', textTransform: 'uppercase' }}>
                            Project
                          </Typography>
                        </Box>
                        <Typography variant="body1" sx={{ fontWeight: 600, color: 'text.primary' }}>
                          {projects.find(p => p.id === selectedProject)?.name}
                        </Typography>
                      </Box>
                    )}

                    {/* Selected Team */}
                    {selectedTeam && (
                      <Box sx={{ 
                        p: 2, 
                        bgcolor: 'success.50', 
                        borderRadius: 1.5,
                        border: '1px solid #bbf7d0',
                        borderLeft: '4px solid #10b981'
                      }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                          <Box sx={{ 
                            width: 8, 
                            height: 8, 
                            bgcolor: 'success.main', 
                            borderRadius: '50%', 
                            mr: 1 
                          }} />
                          <Typography variant="caption" sx={{ fontWeight: 600, color: 'success.main', textTransform: 'uppercase' }}>
                            Team
                          </Typography>
                        </Box>
                        <Typography variant="body1" sx={{ fontWeight: 600, color: 'text.primary', mb: 0.5 }}>
                          {selectedTeam.name}
                        </Typography>
                        {selectedTeam.description && (
                          <Typography variant="body2" color="text.secondary" sx={{ fontSize: '0.875rem' }}>
                            {selectedTeam.description}
                          </Typography>
                        )}
                      </Box>
                    )}
                  </Box>
                ) : (
                  <Box sx={{ 
                    textAlign: 'center', 
                    py: 4,
                    color: 'text.secondary'
                  }}>
                    <Box sx={{ 
                      width: 48, 
                      height: 48, 
                      bgcolor: 'grey.100', 
                      borderRadius: '50%', 
                      display: 'flex', 
                      alignItems: 'center', 
                      justifyContent: 'center',
                      mx: 'auto',
                      mb: 2
                    }}>
                      <ProjectIcon sx={{ color: 'grey.400', fontSize: 24 }} />
                    </Box>
                    <Typography variant="body2">
                      Select a project to get started
                    </Typography>
                  </Box>
                )}
              </Box>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Smart Team Discovery - Full Width */}
      <Grid container spacing={0}>
        <Grid item xs={12}>
          <Card sx={{ minHeight: '75vh' }}>
            <CardContent sx={{ p: 2, height: '100%', display: 'flex', flexDirection: 'column' }}>
              {/* Header with Controls */}
              <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  <TeamIcon sx={{ mr: 1.5, color: 'primary.main', fontSize: 20 }} />
                  <Typography variant="h6" component="h2" sx={{ fontSize: '1.1rem' }}>
                    Smart Team Discovery
                  </Typography>
                  {selectedTeam && (
                    <Chip 
                      label="Selected" 
                      color="success" 
                      size="small" 
                      sx={{ ml: 1.5, fontSize: '0.7rem', height: 20 }} 
                    />
                  )}
                  {selectedProject && teams.length > 0 && (
                    <Chip 
                      label={`${filteredTeams.length} of ${teams.length} teams`}
                      color="primary" 
                      variant="outlined"
                      size="small" 
                      sx={{ ml: 1.5, fontSize: '0.7rem', height: 20 }} 
                    />
                  )}
                </Box>
                <Badge badgeContent={filteredTeams.length} color="primary">
                  <TeamIcon color="action" />
                </Badge>
              </Box>

              {/* Search and Filter Controls - Compact Row */}
              <Box sx={{ mb: 2 }}>
                <Grid container spacing={2} alignItems="center">
                  <Grid item xs={12} md={8}>
                    <TextField
                      fullWidth
                      size="small"
                      placeholder="Search teams by name or description..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      InputProps={{
                        startAdornment: (
                          <InputAdornment position="start">
                            <SearchIcon color="action" fontSize="small" />
                          </InputAdornment>
                        ),
                        endAdornment: searchTerm && (
                          <InputAdornment position="end">
                            <Button
                              size="small"
                              onClick={() => setSearchTerm('')}
                              sx={{ minWidth: 'auto', p: 0.5 }}
                            >
                              <ClearIcon fontSize="small" />
                            </Button>
                          </InputAdornment>
                        ),
                      }}
                    />
                  </Grid>
                  <Grid item xs={12} md={4}>
                    <FormControl fullWidth size="small">
                      <InputLabel>Filter by Group</InputLabel>
                      <Select
                        value={selectedTeamGroup}
                        onChange={(e) => setSelectedTeamGroup(e.target.value)}
                        label="Filter by Group"
                      >
                        <MenuItem value="all">All Teams ({teams.length})</MenuItem>
                        {teamGroups.map((group) => (
                          <MenuItem key={group} value={group}>
                            {group}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  </Grid>
                </Grid>
              </Box>

              {/* Auto-selection Status */}
              {autoSelecting && (
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', py: 3, mb: 2 }}>
                  <CircularProgress size={24} sx={{ mr: 1 }} />
                  <Typography variant="body2" color="text.secondary">
                    🤖 Analyzing your work items to select the best team...
                  </Typography>
                </Box>
              )}

              {/* Auto-selection Result */}
              {autoSelectionResult && (
                <Alert 
                  severity="success" 
                  sx={{ mb: 2 }}
                  action={
                    <Box sx={{ display: 'flex', gap: 1 }}>
                      <Button
                        size="small"
                        onClick={() => setShowSelectionReason(!showSelectionReason)}
                      >
                        {showSelectionReason ? 'Hide' : 'Why?'}
                      </Button>
                      <Button
                        size="small"
                        variant="outlined"
                        onClick={() => {
                          setAutoSelectionResult(null);
                          setSelectedTeam(null);
                        }}
                      >
                        Change Team
                      </Button>
                    </Box>
                  }
                >
                  <Typography variant="body2">
                    <strong>Auto-selected:</strong> {autoSelectionResult.selectedTeam.name}
                    <br />
                    <Typography variant="caption">
                      Reason: {autoSelectionResult.selectedTeam.reasons?.join(', ') || 'Intelligent selection'}
                      {autoSelectionResult.selectedTeam.confidence && 
                        ` (${Math.round(autoSelectionResult.selectedTeam.confidence * 100)}% confidence)`
                      }
                    </Typography>
                  </Typography>
                </Alert>
              )}

              {/* Selection Reason Details */}
              {showSelectionReason && autoSelectionResult && (
                <Collapse in={showSelectionReason}>
                  <Box sx={{ mb: 2, p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
                    <Typography variant="subtitle2" gutterBottom>
                      Selection Details:
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      • <strong>Method:</strong> {autoSelectionResult.selectionMethod || 'Intelligent Selection'}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      • <strong>Confidence:</strong> {Math.round(autoSelectionResult.selectedTeam.confidence * 100)}%
                    </Typography>
                    {autoSelectionResult.alternatives && autoSelectionResult.alternatives.length > 0 && (
                      <Typography variant="body2" color="text.secondary">
                        • <strong>Alternatives:</strong> {autoSelectionResult.alternatives.map(alt => alt.name).join(', ')}
                      </Typography>
                    )}
                    <Typography variant="body2" color="text.secondary">
                      • <strong>Reasons:</strong> {autoSelectionResult.selectedTeam.reasons?.join(', ')}
                    </Typography>
                  </Box>
                </Collapse>
              )}

              {/* Teams List - Full Width Grid */}
              <Box sx={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
                {loading.teams ? (
                  <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
                    <CircularProgress />
                  </Box>
                ) : (
                  <Box sx={{ flex: 1, overflow: 'auto', minHeight: 0 }}>
                    {filteredTeams.length > 0 ? (
                      <Grid container spacing={2}>
                        {filteredTeams.map((team) => {
                          const isSelected = selectedTeam?.id === team.id;
                          const isAutoSelected = autoSelectionResult && autoSelectionResult.selectedTeam && autoSelectionResult.selectedTeam.id === team.id;
                          
                          return (
                            <Grid item xs={12} sm={6} md={4} lg={3} xl={2} key={team.id}>
                              <Card
                                variant="outlined"
                                sx={{
                                  cursor: 'pointer',
                                  transition: 'all 0.2s ease-in-out',
                                  border: isSelected ? '2px solid' : '1px solid',
                                  borderColor: isSelected ? 'primary.main' : 'divider',
                                  backgroundColor: isSelected ? 'primary.50' : 'transparent',
                                  height: '100%',
                                  '&:hover': {
                                    borderColor: 'primary.main',
                                    boxShadow: 2,
                                    transform: 'translateY(-1px)',
                                  },
                                }}
                                onClick={() => handleTeamSelect(team)}
                              >
                                <CardContent sx={{ p: 2, height: '100%', display: 'flex', flexDirection: 'column' }}>
                                  <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', mb: 1 }}>
                                    <Box sx={{ flex: 1, minWidth: 0 }}>
                                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                                        <Typography
                                          variant="subtitle2"
                                          sx={{
                                            fontWeight: isSelected ? 600 : 500,
                                            color: isSelected ? 'primary.main' : 'text.primary',
                                            wordBreak: 'break-word',
                                            fontSize: '0.9rem',
                                            fontStyle: team.verified ? 'italic' : 'normal',
                                          }}
                                        >
                                          {team.name}
                                          {team.verified && (
                                            <Chip
                                              size="small"
                                              label="✓"
                                              sx={{
                                                ml: 1,
                                                height: 16,
                                                fontSize: '0.7rem',
                                                backgroundColor: 'success.light',
                                                color: 'success.contrastText',
                                              }}
                                            />
                                          )}
                                        </Typography>
                                        {isAutoSelected && (
                                          <Chip
                                            label="🤖"
                                            size="small"
                                            color="success"
                                            variant="outlined"
                                            sx={{ fontSize: '0.6rem', height: 18, minWidth: 24 }}
                                          />
                                        )}
                                      </Box>
                                      {team.description && (
                                        <Typography
                                          variant="caption"
                                          color="text.secondary"
                                          sx={{
                                            display: '-webkit-box',
                                            WebkitLineClamp: 3,
                                            WebkitBoxOrient: 'vertical',
                                            overflow: 'hidden',
                                            fontSize: '0.75rem',
                                            lineHeight: 1.2,
                                          }}
                                        >
                                          {team.description}
                                        </Typography>
                                      )}
                                    </Box>
                                    <Box sx={{ ml: 1, flexShrink: 0 }}>
                                      {isSelected ? (
                                        <SelectedIcon 
                                          sx={{ color: 'primary.main', fontSize: 18 }} 
                                        />
                                      ) : (
                                        <UnselectedIcon 
                                          sx={{ color: 'text.secondary', fontSize: 18 }} 
                                        />
                                      )}
                                    </Box>
                                  </Box>
                                </CardContent>
                              </Card>
                            </Grid>
                          );
                        })}
                      </Grid>
                    ) : (
                      <Box sx={{ 
                        display: 'flex', 
                        flexDirection: 'column', 
                        alignItems: 'center', 
                        justifyContent: 'center', 
                        height: '100%', 
                        minHeight: 300,
                        p: 3,
                        textAlign: 'center'
                      }}>
                        <TeamIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
                        <Typography variant="body1" color="text.secondary" gutterBottom>
                          {searchTerm || selectedTeamGroup !== 'all' 
                            ? 'No teams match your search criteria' 
                            : 'No teams found'
                          }
                        </Typography>
                        {searchTerm || selectedTeamGroup !== 'all' ? (
                          <Button
                            onClick={() => {
                              setSearchTerm('');
                              setSelectedTeamGroup('all');
                            }}
                            startIcon={<ClearIcon />}
                            size="small"
                            variant="outlined"
                          >
                            Clear filters
                          </Button>
                        ) : (
                          <Typography variant="body2" color="text.secondary">
                            Make sure you have access to teams in this project
                          </Typography>
                        )}
                      </Box>
                    )}
                  </Box>
                )}
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

    </Container>
  );
};

export default TeamSelection;

