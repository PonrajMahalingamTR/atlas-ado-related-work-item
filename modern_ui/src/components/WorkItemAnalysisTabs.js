import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Container,
  Paper,
  Typography,
  Tabs,
  Tab,
  Card,
  CardContent,
  Chip,
  IconButton,
  Tooltip,
  Alert,
  CircularProgress,
  Fade,
  Slide,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Button,
  Collapse,
  CardHeader,
  InputAdornment,
} from '@mui/material';
import {
  ViewList as ListIcon,
  Analytics as AnalysisIcon,
  Refresh as RefreshIcon,
  ArrowBack as BackIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  RestartAlt as ResetIcon,
  Person as PersonIcon,
  Folder as FolderIcon,
  Search as SearchIcon,
  Psychology as BrainIcon,
  AttachMoney as MoneyIcon,
  Memory as TokenIcon,
  Work as WorkIcon,
  OpenInNew as OpenInNewIcon,
  Psychology as AIIcon,
} from '@mui/icons-material';

import WorkItemsList from './WorkItemsList';
import WorkItemAnalysis from './WorkItemAnalysis';
import { ModelIcon, getModelDisplayName } from './ModelIcon';
import { fetchFilterOptions, fetchTeams, getCurrentTeam, fetchWorkItems, fetchCurrentModel } from '../services/api';

const WorkItemAnalysisTabs = ({ connectionStatus, autoSelectedTeam }) => {
  const { workItemId } = useParams();
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState(0);
  const [selectedWorkItemId, setSelectedWorkItemId] = useState(null);
  const [workItemData, setWorkItemData] = useState(null);
  
  // Filter states
  const [filtersExpanded, setFiltersExpanded] = useState(false);
  const [filters, setFilters] = useState({
    search: '',
    team: 'All',
    work_item_type: 'All',
    state: 'All',
    assigned_to: 'All',
    area_path: 'All',
  });
  const [filterOptions, setFilterOptions] = useState({
    workItemTypes: [],
    states: [],
    assignedTo: [],
    areaPaths: [],
    teams: [],
  });
  
  // Loading state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  // Analysis data state
  const [analysisData, setAnalysisData] = useState(null);
  const [currentModel, setCurrentModel] = useState(null);
  
  // LLM Analysis state
  const [runningAnalysis, setRunningAnalysis] = useState(false);
  const [refinedWorkItems, setRefinedWorkItems] = useState([]);
  const [workflowStep, setWorkflowStep] = useState('initial');

  // Load filter options and current model on component mount
  useEffect(() => {
    if (connectionStatus.azure_devops.connected) {
      loadFilterOptions();
      loadCurrentModel();
    }
  }, [connectionStatus.azure_devops.connected]);

  // Handle auto-selected team when it becomes available
  useEffect(() => {
    if (autoSelectedTeam && autoSelectedTeam.team && filterOptions.teams.length > 0) {
      console.log('🎯 Auto-selected team received, updating team filter:', autoSelectedTeam.team.name);
      setFilters(prev => ({
        ...prev,
        team: autoSelectedTeam.team.name
      }));
    }
  }, [autoSelectedTeam, filterOptions.teams]);

  // Handle URL parameters - if workItemId is in URL, switch to analysis tab
  useEffect(() => {
    if (workItemId) {
      setSelectedWorkItemId(workItemId);
      setActiveTab(1);
      // Clear the URL parameter
      navigate('/work-items-tabs', { replace: true });
    }
  }, [workItemId, navigate]);

  const handleTabChange = (event, newValue) => {
    setActiveTab(newValue);
  };

  const handleWorkItemSelect = (workItemId, workItem = null) => {
    console.log('Work item selected:', workItemId, workItem);
    setSelectedWorkItemId(workItemId);
    if (workItem) {
      setWorkItemData(workItem);
    }
    // Switch to analysis tab when work item is selected
    setActiveTab(1);
  };

  const handleBackToList = () => {
    setActiveTab(0);
  };

  const handleAnalysisDataUpdate = (data) => {
    setAnalysisData(data);
  };


  const loadCurrentModel = async () => {
    try {
      const model = await fetchCurrentModel();
      setCurrentModel(model);
    } catch (err) {
      console.error('Error loading current model:', err);
    }
  };

  const handleFilterChange = (filterName, value) => {
    setFilters(prev => {
      const newFilters = {
        ...prev,
        [filterName]: value
      };
      // Remove the load trigger when filters change to prevent accidental loading
      delete newFilters._loadTrigger;
      return newFilters;
    });
  };

  const handleClearFilters = () => {
    setFilters({
      search: '',
      team: 'All',
      work_item_type: 'All',
      state: 'All',
      assigned_to: 'All',
      area_path: 'All',
    });
    // Note: No _loadTrigger here, so clearing filters won't trigger a load
  };

  const loadFilterOptions = async () => {
    try {
      console.log('Loading filter options...');
      
      // Load filter options and teams in parallel
      const [filterOptionsData, teamsData, currentTeamData] = await Promise.all([
        fetchFilterOptions(),
        fetchTeams(),
        getCurrentTeam().catch(() => ({ name: '', id: '' })) // Fallback if no current team
      ]);
      
      // Extract team data from teams data (handle new response structure)
      const teamsArray = teamsData?.teams || teamsData || [];
      const teamObjects = Array.isArray(teamsArray) ? teamsArray : [];
      
      // Set filter options with dynamic teams (store full team objects to preserve verification status)
      const updatedFilterOptions = {
        ...(filterOptionsData || {}),
        teams: teamObjects,
        workItemTypes: filterOptionsData?.workItemTypes || [],
        states: filterOptionsData?.states || [],
        assignedTo: filterOptionsData?.assignedTo || [],
        areaPaths: filterOptionsData?.areaPaths || [],
      };
      
      setFilterOptions(updatedFilterOptions);
      
      // Set default team from current team selection
      const defaultTeam = currentTeamData?.name || (teamObjects[0]?.name) || 'All';
      setFilters(prev => ({
        ...prev,
        team: defaultTeam
      }));
      
      console.log('Filter options loaded:', updatedFilterOptions);
      console.log('Default team set to:', defaultTeam);
    } catch (err) {
      console.error('Error loading filter options:', err);
      // Set empty options on error
      setFilterOptions({
        workItemTypes: [],
        states: [],
        assignedTo: [],
        areaPaths: [],
        teams: [],
      });
    }
  };

  const handleLoadWorkItems = async () => {
    try {
      setLoading(true);
      setError('');
      
      console.log('Loading work items with filters:', filters);
      
      // Force WorkItemsList to load data by passing a trigger prop
      // Use a unique timestamp to ensure single trigger per click
      const triggerTime = Date.now();
      setFilters(prev => ({ 
        ...prev, 
        _loadTrigger: triggerTime // Add a trigger to force data loading
      }));
      
      console.log('Work items loading triggered with filters:', filters, 'trigger:', triggerTime);
      
    } catch (err) {
      console.error('Error loading work items:', err);
      setError('Failed to load work items. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const TabPanel = ({ children, value, index, ...other }) => {
    return (
      <div
        role="tabpanel"
        hidden={value !== index}
        id={`work-item-tabpanel-${index}`}
        aria-labelledby={`work-item-tab-${index}`}
        {...other}
      >
        {value === index && (
          <Box sx={{ pt: 0 }}>
            {children}
          </Box>
        )}
      </div>
    );
  };

  return (
    <Container maxWidth="xl" sx={{ py: 3 }}>
      {/* Modern Header with Tabs */}
      <Paper 
        elevation={0} 
        sx={{ 
          mb: 3, 
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          color: 'white',
          borderRadius: 3,
          overflow: 'hidden',
          position: 'relative'
        }}
      >
        <Box sx={{ p: 3, pb: 0, position: 'relative' }}>
          {/* Title, Tabs and Analysis Information Row - 50/50 split with balanced spacing */}
          <Box sx={{ display: 'flex', alignItems: 'stretch', minHeight: 120 }}>
            {/* Left Section - 50% width (Title + Tabs) */}
            <Box sx={{ 
              width: '50%', 
              display: 'flex', 
              flexDirection: 'column',
              pr: 2,
              justifyContent: 'space-between'
            }}>
              {/* Title Section */}
              <Box sx={{ 
                display: 'flex', 
                alignItems: 'center',
                flex: 1
              }}>
                <Box sx={{ 
                  bgcolor: 'rgba(255,255,255,0.2)', 
                  borderRadius: 2, 
                  p: 1.5, 
                  mr: 2,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0
                }}>
                  <AnalysisIcon sx={{ fontSize: 28, color: 'white' }} />
                </Box>
                <Box sx={{ flex: 1 }}>
                  <Typography variant="h4" component="h1" fontWeight={600} sx={{ color: 'white' }}>
                    ADO Task Learning And Semantic System
                  </Typography>
                  <Typography variant="body1" sx={{ color: 'rgba(255,255,255,0.8)', mt: 0.5 }}>
                    Discover Related ADO Work Items with AI Intelligence
                  </Typography>
                </Box>
              </Box>
              
              {/* Tabs Section - Positioned at bottom */}
              <Tabs
                value={activeTab}
                onChange={handleTabChange}
                sx={{
                  alignSelf: 'flex-start',
                  '& .MuiTab-root': {
                    color: 'rgba(255,255,255,0.7)',
                    fontWeight: 500,
                    textTransform: 'none',
                    fontSize: '1rem',
                    minHeight: 48,
                    '&.Mui-selected': {
                      color: 'white',
                      fontWeight: 600,
                    },
                    '&:hover': {
                      color: 'white',
                      backgroundColor: 'rgba(255,255,255,0.1)',
                    }
                  },
                  '& .MuiTabs-indicator': {
                    backgroundColor: 'white',
                    height: 3,
                    borderRadius: '2px 2px 0 0',
                  }
                }}
              >
                <Tab 
                  icon={<ListIcon />} 
                  iconPosition="start"
                  label="Select Work Item" 
                  id="work-item-tab-0"
                  aria-controls="work-item-tabpanel-0"
                />
                <Tab 
                  icon={<AnalysisIcon />} 
                  iconPosition="start"
                  label="AI Insights" 
                  id="work-item-tab-1"
                  aria-controls="work-item-tabpanel-1"
                  disabled={!selectedWorkItemId}
                />
              </Tabs>
            </Box>
            
            {/* Analysis Information - 50% width with balanced vertical positioning */}
            <Box sx={{ 
              width: '50%',
              display: 'flex',
              justifyContent: 'flex-end',
              alignItems: 'center',
              pl: 2,
              mb: 2
            }}>
              <Box sx={{ 
                bgcolor: 'rgba(255,255,255,0.95)',
                borderRadius: 2,
                p: 2,
                minWidth: 200,
                maxWidth: 250,
                boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                backdropFilter: 'blur(10px)',
                alignSelf: 'center'
              }}>
                <Typography variant="h6" gutterBottom color="primary" sx={{ fontSize: '1rem', fontWeight: 600, mb: 1 }}>
                  Analysis Information
                </Typography>
                <Box display="flex" flexDirection="column" gap={0.5}>
                  {/* Pre-analysis: Show only selected model */}
                  <Box display="flex" alignItems="center" gap={1}>
                    <ModelIcon modelId={currentModel?.model} sx={{ fontSize: 16 }} />
                    <Typography variant="body2" color="text.secondary">
                      Model: {getModelDisplayName(currentModel?.model)}
                    </Typography>
                  </Box>
                  
                  {/* Post-analysis: Show tokens and cost (updated via DOM manipulation) */}
                  <Box display="flex" alignItems="center" gap={1}>
                    <TokenIcon sx={{ fontSize: 16, color: 'primary.main' }} />
                    <Typography variant="body2" color="text.secondary" data-cost-info="tokens">
                      Tokens: 0
                    </Typography>
                  </Box>
                  <Box display="flex" alignItems="center" gap={1}>
                    <MoneyIcon sx={{ fontSize: 16, color: 'success.main' }} />
                    <Typography variant="body2" color="text.secondary" data-cost-info="cost">
                      Cost: $0.00
                    </Typography>
                  </Box>
                </Box>
              </Box>
            </Box>
          </Box>
        </Box>


        {/* Error Display */}
        {error && (
          <Alert severity="error" sx={{ m: 2 }}>
            {error}
          </Alert>
        )}

        {/* Selected Work Item Box - Show only in Tab 2 (AI Insights) when work item is selected */}
        {activeTab === 1 && selectedWorkItemId && workItemData && (
          <Box sx={{ 
            p: 3, 
            pt: 2, 
            bgcolor: 'rgba(255,255,255,0.1)',
            borderTop: '1px solid rgba(255,255,255,0.2)'
          }}>
            <Card sx={{ 
              bgcolor: 'rgba(255,255,255,0.95)', 
              backdropFilter: 'blur(10px)',
              boxShadow: '0 4px 20px rgba(0,0,0,0.1)',
              p: 3
            }}>
              <Box display="flex" alignItems="center" gap={2} mb={2}>
                <Box sx={{ 
                  bgcolor: 'primary.main', 
                  color: 'white', 
                  borderRadius: '50%', 
                  p: 1, 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'center' 
                }}>
                  <WorkIcon />
                </Box>
                <Box>
                  <Typography variant="h6" color="primary">
                    Selected Work Item
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    This is the work item you're analyzing
                  </Typography>
                </Box>
              </Box>
              
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', minHeight: 80 }}>
                {/* Left side - Work Item Details */}
                <Box sx={{ flex: 1, mr: 3, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                  <Box>
                    <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      #{workItemData.id} - {workItemData.title}
                      <OpenInNewIcon fontSize="small" />
                    </Typography>
                  </Box>
                  
                  <Box display="flex" gap={1} flexWrap="wrap" mt={1}>
                    <Chip
                      label={workItemData.state}
                      color="primary"
                      variant="outlined"
                      size="small"
                    />
                    <Chip
                      label={workItemData.type}
                      color="primary"
                      variant="filled"
                      size="small"
                    />
                    {workItemData.assignedTo && (
                      <Chip
                        label={`Assigned to: ${workItemData.assignedTo}`}
                        variant="outlined"
                        size="small"
                      />
                    )}
                    <Chip
                      label={`Area: ${workItemData.areaPath}`}
                      variant="outlined"
                      size="small"
                    />
                  </Box>
                </Box>

              </Box>
            </Card>
          </Box>
        )}

        {/* Filters & Search Bar - Show only in Tab 1 (Select Work Item) */}
        {activeTab === 0 && (
          <Fade in={true} timeout={500}>
            <Box sx={{ 
              p: 3, 
              pt: 2, 
              bgcolor: 'rgba(255,255,255,0.1)',
              borderTop: '1px solid rgba(255,255,255,0.2)'
            }}>
            <Card sx={{ 
              bgcolor: 'rgba(255,255,255,0.95)', 
              backdropFilter: 'blur(10px)',
              boxShadow: '0 4px 20px rgba(0,0,0,0.1)'
            }}>
              {/* First Row - Always Visible */}
              <Box sx={{ px: 3, py: 2 }}>
                <Grid container spacing={2} alignItems="flex-start">
                  {/* Team Selection */}
                  <Grid item xs={12} md={3}>
                    <FormControl fullWidth size="small">
                      <InputLabel>Team</InputLabel>
                      <Select
                        value={filters.team}
                        onChange={(e) => handleFilterChange('team', e.target.value)}
                        label="Team"
                      >
                        <MenuItem value="All">All Teams</MenuItem>
                        {filterOptions.teams?.map((team) => (
                          <MenuItem key={typeof team === 'string' ? team : team.id || team.name || 'unknown'} value={typeof team === 'string' ? team : team.name || 'Unknown Team'}>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              <Typography
                                sx={{
                                  fontStyle: team.verified ? 'italic' : 'normal',
                                  fontWeight: team.verified ? 500 : 400,
                                }}
                              >
                                {typeof team === 'string' ? team : team.name || 'Unknown Team'}
                              </Typography>
                              {team.verified && (
                                <Box
                                  sx={{
                                    width: 16,
                                    height: 16,
                                    borderRadius: '50%',
                                    backgroundColor: 'success.light',
                                    color: 'success.contrastText',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    fontSize: '0.7rem',
                                    fontWeight: 'bold',
                                  }}
                                >
                                  ✓
                                </Box>
                              )}
                            </Box>
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  </Grid>

                  {/* Work Item Type */}
                  <Grid item xs={12} md={3}>
                    <FormControl fullWidth size="small">
                      <InputLabel>Type</InputLabel>
                      <Select
                        value={filters.work_item_type}
                        onChange={(e) => handleFilterChange('work_item_type', e.target.value)}
                        label="Type"
                      >
                        <MenuItem value="All">All Types</MenuItem>
                        {filterOptions.workItemTypes?.map((type) => (
                          <MenuItem key={type} value={type}>
                            {type}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  </Grid>

                  {/* State */}
                  <Grid item xs={12} md={3}>
                    <FormControl fullWidth size="small">
                      <InputLabel>State</InputLabel>
                      <Select
                        value={filters.state}
                        onChange={(e) => handleFilterChange('state', e.target.value)}
                        label="State"
                      >
                        <MenuItem value="All">All States</MenuItem>
                        {filterOptions.states?.map((state) => (
                          <MenuItem key={state} value={state}>
                            {state}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  </Grid>

                  {/* Load Work Items Button */}
                  <Grid item xs={6} md={1.5}>
                    <Button
                      variant="contained"
                      startIcon={loading ? <CircularProgress size={16} color="inherit" /> : <RefreshIcon />}
                      onClick={handleLoadWorkItems}
                      disabled={loading}
                      size="small"
                      fullWidth
                      sx={{ 
                        height: '40px',
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
                      {loading ? 'Loading...' : 'Load'}
                    </Button>
                  </Grid>

                  {/* Reset Button with Collapse Arrow */}
                  <Grid item xs={6} md={1.5}>
                    <Box sx={{ display: 'flex', gap: 1 }}>
                      <Button
                        variant="outlined"
                        startIcon={<ResetIcon />}
                        onClick={handleClearFilters}
                        size="small"
                        sx={{ height: '40px', flex: 1 }}
                      >
                        Reset
                      </Button>
                      <IconButton
                        onClick={() => setFiltersExpanded(!filtersExpanded)}
                        aria-label="expand filters"
                        size="small"
                        sx={{ 
                          height: '40px', 
                          width: '40px',
                          border: '1px solid',
                          borderColor: 'divider',
                          borderRadius: 1
                        }}
                      >
                        {filtersExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                      </IconButton>
                    </Box>
                  </Grid>
                </Grid>
              </Box>

              {/* Second Row - Collapsible */}
              <Collapse in={filtersExpanded} timeout="auto" unmountOnExit>
                <CardContent sx={{ pt: 0 }}>
                  <Grid container spacing={2} alignItems="center">
                    {/* Search */}
                    <Grid item xs={12} md={4}>
                      <TextField
                        fullWidth
                        label="Search"
                        value={filters.search}
                        onChange={(e) => handleFilterChange('search', e.target.value)}
                        placeholder="Search by title, ID, or assignee..."
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

                    {/* Assigned To */}
                    <Grid item xs={12} md={4}>
                      <FormControl fullWidth size="small">
                        <InputLabel>Assignee</InputLabel>
                        <Select
                          value={filters.assigned_to}
                          onChange={(e) => handleFilterChange('assigned_to', e.target.value)}
                          label="Assignee"
                          startAdornment={
                            <InputAdornment position="start">
                              <PersonIcon />
                            </InputAdornment>
                          }
                        >
                          <MenuItem value="All">All Users</MenuItem>
                          {filterOptions.assignedTo?.map((user) => (
                            <MenuItem key={user} value={user}>
                              {user}
                            </MenuItem>
                          ))}
                        </Select>
                      </FormControl>
                    </Grid>

                    {/* Area Path */}
                    <Grid item xs={12} md={4}>
                      <FormControl fullWidth size="small">
                        <InputLabel>Area Path</InputLabel>
                        <Select
                          value={filters.area_path}
                          onChange={(e) => handleFilterChange('area_path', e.target.value)}
                          label="Area Path"
                          startAdornment={
                            <InputAdornment position="start">
                              <FolderIcon />
                            </InputAdornment>
                          }
                        >
                          <MenuItem value="All">All Areas</MenuItem>
                          {filterOptions.areaPaths?.map((path) => (
                            <MenuItem key={path} value={path}>
                              {path.split('\\').pop() || path}
                            </MenuItem>
                          ))}
                        </Select>
                      </FormControl>
                    </Grid>
                  </Grid>
                </CardContent>
              </Collapse>
            </Card>
          </Box>
        </Fade>
        )}
      </Paper>

      {/* Tab Content */}
      <TabPanel value={activeTab} index={0}>
        <Slide direction="right" in={activeTab === 0} timeout={300}>
          <Box>
            <WorkItemsList 
              connectionStatus={connectionStatus}
              onWorkItemSelect={handleWorkItemSelect}
              hideHeader={true}
              externalFilters={filters}
            />
          </Box>
        </Slide>
      </TabPanel>

      <TabPanel value={activeTab} index={1}>
        <Slide direction="left" in={activeTab === 1} timeout={300}>
          <Box>
            {selectedWorkItemId ? (
              <WorkItemAnalysis 
                connectionStatus={connectionStatus}
                workItemId={selectedWorkItemId}
                workItem={workItemData}
                onBackToList={handleBackToList}
                onAnalysisDataUpdate={handleAnalysisDataUpdate}
                runningAnalysis={runningAnalysis}
                setRunningAnalysis={setRunningAnalysis}
                refinedWorkItems={refinedWorkItems}
                setRefinedWorkItems={setRefinedWorkItems}
                workflowStep={workflowStep}
                setWorkflowStep={setWorkflowStep}
              />
            ) : (
              <Paper sx={{ p: 4, textAlign: 'center' }}>
                <AnalysisIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
                <Typography variant="h6" color="text.secondary" gutterBottom>
                  No Work Item Selected
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Please select a work item from the list to begin analysis
                </Typography>
              </Paper>
            )}
          </Box>
        </Slide>
      </TabPanel>
    </Container>
  );
};

export default WorkItemAnalysisTabs;
