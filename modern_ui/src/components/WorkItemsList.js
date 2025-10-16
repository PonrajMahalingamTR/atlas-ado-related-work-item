import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Container,
  Paper,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  TextField,
  Button,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  IconButton,
  Tooltip,
  Alert,
  CircularProgress,
  Card,
  CardContent,
} from '@mui/material';
import {
  Search as SearchIcon,
  FilterList as FilterIcon,
  Analytics as AnalysisIcon,
  Refresh as RefreshIcon,
  Clear as ClearIcon,
  ViewList as ViewListIcon,
} from '@mui/icons-material';

import { 
  fetchWorkItems, 
  fetchFilterOptions, 
  formatApiError 
} from '../services/api';

const WorkItemsList = ({ connectionStatus, onWorkItemSelect, hideHeader = false, externalFilters = null, onFiltersChange = null }) => {
  const navigate = useNavigate();
  
  // State management
  const [workItems, setWorkItems] = useState([]);
  const [filteredWorkItems, setFilteredWorkItems] = useState([]);
  const [filterOptions, setFilterOptions] = useState({
    workItemTypes: [],
    states: [],
    assignedTo: [],
    areaPaths: [],
    iterationPaths: [],
    teams: [],
  });
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [dataLoaded, setDataLoaded] = useState(false);
  const [restoringState, setRestoringState] = useState(false);
  const lastTriggerTimeRef = useRef(0);
  
  // Pagination
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  
  
  // Filters
  const [filters, setFilters] = useState({
    search: '',
    team: 'All',
    work_item_type: 'All',
    state: 'All',
    assigned_to: 'All',
    area_path: 'All',
    iteration_path: 'All',
  });

  // Use external filters if provided
  const currentFilters = externalFilters || filters;
  

  // Define applyFilters with useCallback to prevent dependency changes
  const applyFilters = useCallback(() => {
    console.log('🔍 Applying filters...', { workItemsCount: workItems?.length, filters: currentFilters });
    
    if (!workItems || workItems.length === 0) {
      console.log('⚠️ No work items to filter');
      setFilteredWorkItems([]);
      return;
    }
    
    let filtered = [...workItems];
    console.log(`📊 Starting with ${filtered.length} work items`);

    // Apply search filter
    if (currentFilters.search) {
      const searchTerm = currentFilters.search.toLowerCase();
      const beforeSearch = filtered.length;
      filtered = filtered.filter(item =>
        item.title.toLowerCase().includes(searchTerm) ||
        item.id.toString().includes(searchTerm) ||
        (item.assignedTo && item.assignedTo.toLowerCase().includes(searchTerm)) ||
        (item.description && item.description.toLowerCase().includes(searchTerm))
      );
      console.log(`🔍 Search filter "${searchTerm}": ${beforeSearch} -> ${filtered.length} items`);
    }

    // Apply dropdown filters
    Object.entries(currentFilters).forEach(([key, value]) => {
      if (value !== 'All' && value !== '' && key !== 'search') {
        const beforeFilter = filtered.length;
        switch (key) {
          case 'team':
            // Filter by team - the backend should have already filtered correctly
            // This frontend filtering is mainly for additional client-side filtering
            if (value === 'All') {
              // Show all items if "All" is selected
              console.log(`🔍 Team filter: Showing all items (${filtered.length} items)`);
            } else {
              const beforeTeamFilter = filtered.length;
              console.log(`🔍 Team filter: Filtering ${beforeTeamFilter} items for team "${value}"`);
              
              // Log first few items before filtering
              if (filtered.length > 0) {
                console.log(`🔍 Sample items before team filter:`);
                filtered.slice(0, 3).forEach((item, idx) => {
                  console.log(`  ${idx + 1}. ID=${item.id}, AreaPath="${item.areaPath}"`);
                });
              }
              
              filtered = filtered.filter(item => {
                const areaPath = item.areaPath || '';
                const teamName = value.toLowerCase();
                
                // Special handling for specific teams with known area path patterns
                let matches = false;
                
                if (teamName === 'practical law - ai optimization-core') {
                  matches = areaPath.toLowerCase().includes('practical law ai optimization-core');
                } else if (teamName === 'practicallaw-aideliveryteam1') {
                  matches = areaPath.toLowerCase().includes('practicallaw\\aideliveryteam1');
                } else if (teamName === 'practicallaw-aideliveryteam2') {
                  matches = areaPath.toLowerCase().includes('practicallaw\\aideliveryteam2');
                } else if (teamName === 'wlus accessibility') {
                  matches = areaPath.toLowerCase().includes('wlus\\accessibility');
                } else {
                  // For other teams, try flexible matching
                  const normalizeString = (str) => str.replace(/\s*-\s*/g, ' - ').toLowerCase();
                  const normalizedAreaPath = normalizeString(areaPath);
                  const normalizedTeamName = normalizeString(teamName);
                  
                  // Try multiple matching strategies
                  matches = normalizedAreaPath.includes(normalizedTeamName) || 
                         normalizedAreaPath.endsWith('\\' + normalizedTeamName) ||
                         areaPath.toLowerCase().includes(teamName.replace(/\s*-\s*/g, '-')) ||
                         areaPath.toLowerCase().endsWith('\\' + teamName.replace(/\s*-\s*/g, '-')) ||
                         // Try converting team name to area path format: "Team-Name" -> "team\\name"
                         areaPath.toLowerCase().includes(teamName.replace(/-/g, '\\')) ||
                         // Try with spaces converted to backslashes: "Team Name" -> "team\\name"
                         areaPath.toLowerCase().includes(teamName.replace(/\s+/g, '\\'));
                }
                
                if (!matches && areaPath) {
                  console.log(`❌ Team filter mismatch: areaPath="${areaPath}" vs teamName="${teamName}"`);
                } else if (matches) {
                  console.log(`✅ Team filter match: areaPath="${areaPath}" vs teamName="${teamName}"`);
                }
                
                return matches;
              });
              
              const afterTeamFilter = filtered.length;
              console.log(`🔍 Team filter result: ${beforeTeamFilter} -> ${afterTeamFilter} items (team: "${value}")`);
              
              // Log first few items after filtering
              if (filtered.length > 0) {
                console.log(`🔍 Sample items after team filter:`);
                filtered.slice(0, 3).forEach((item, idx) => {
                  console.log(`  ${idx + 1}. ID=${item.id}, AreaPath="${item.areaPath}"`);
                });
              } else {
                console.log(`❌ No items remaining after team filter!`);
              }
            }
            break;
          case 'work_item_type':
            filtered = filtered.filter(item => item.type === value);
            break;
          case 'state':
            filtered = filtered.filter(item => item.state === value);
            break;
          case 'assigned_to':
            filtered = filtered.filter(item => item.assignedTo === value);
            break;
          case 'area_path':
            filtered = filtered.filter(item => item.areaPath === value);
            break;
          case 'iteration_path':
            filtered = filtered.filter(item => item.iterationPath === value);
            break;
          default:
            break;
        }
        console.log(`🔧 Filter ${key}="${value}": ${beforeFilter} -> ${filtered.length} items`);
      }
    });

    // Sort by ID in descending order (newest first)
    filtered.sort((a, b) => b.id - a.id);
    
    console.log(`✅ Final filtered result: ${filtered.length} items (sorted by ID descending)`);
    setFilteredWorkItems(filtered);
    setPage(0); // Reset to first page when filters change
  }, [workItems, filters]);

  // Define restoreSavedState without dependencies to avoid circular loops
  const restoreSavedState = useCallback(() => {
    try {
      const savedState = sessionStorage.getItem('workItemsState');
      if (savedState) {
        console.log('🔄 Restoring saved state from session storage');
        setRestoringState(true);
        const parsedState = JSON.parse(savedState);
        
        console.log('📦 Parsed saved state:', parsedState);
        
        // Restore filters first
        if (parsedState.filters) {
          console.log('🔧 Restoring filters:', parsedState.filters);
          setFilters(parsedState.filters);
        }
        
        // Restore data loaded state (work items are not saved to avoid quota issues)
        if (parsedState.dataLoaded) {
          console.log(`📊 Restoring data loaded state (work items count: ${parsedState.workItemsCount || 0})`);
          setDataLoaded(parsedState.dataLoaded);
          
          // Note: Work items are not restored from session storage to avoid quota exceeded
          // They will need to be reloaded when the user clicks Load
          console.log('ℹ️ Work items not restored from session storage (quota optimization)');
        } else {
          console.log('⚠️ No dataLoaded flag in saved state');
        }
        
        // Restore pagination
        if (parsedState.page !== undefined) {
          console.log('📄 Restoring page:', parsedState.page);
          setPage(parsedState.page);
        }
        if (parsedState.rowsPerPage !== undefined) {
          console.log('📄 Restoring rows per page:', parsedState.rowsPerPage);
          setRowsPerPage(parsedState.rowsPerPage);
        }
        
        // Clear restoring state after a short delay
        setTimeout(() => {
          console.log('✅ State restoration completed');
          setRestoringState(false);
        }, 500);
      } else {
        console.log('ℹ️ No saved state found in session storage');
      }
    } catch (error) {
      console.error('❌ Error restoring saved state:', error);
      setRestoringState(false);
    }
  }, []); // No dependencies to avoid circular loops

  // Load filter options on component mount (but not work items)
  useEffect(() => {
    if (connectionStatus.azure_devops.connected) {
      loadFilterOptions();
      // Restore saved state from session storage
      restoreSavedState();
    }
  }, [connectionStatus.azure_devops.connected]); // Remove restoreSavedState from dependencies

  // Load work items when Load button is clicked (indicated by _loadTrigger in externalFilters)
  useEffect(() => {
    if (externalFilters && externalFilters._loadTrigger && connectionStatus.azure_devops.connected) {
      // Prevent duplicate calls by checking if this is a new trigger using ref
      if (externalFilters._loadTrigger !== lastTriggerTimeRef.current) {
        console.log('Load button clicked, loading work items with filters...', externalFilters);
        console.log('Previous trigger time:', lastTriggerTimeRef.current, 'New trigger time:', externalFilters._loadTrigger);
        lastTriggerTimeRef.current = externalFilters._loadTrigger;
        loadData();
      } else {
        console.log('Duplicate load trigger detected, skipping...', externalFilters._loadTrigger);
        console.log('Previous trigger time:', lastTriggerTimeRef.current, 'Current trigger time:', externalFilters._loadTrigger);
      }
    }
  }, [externalFilters?._loadTrigger, connectionStatus.azure_devops.connected]);

  // Fallback: If no data is loaded after a reasonable time, show the empty state
  useEffect(() => {
    const fallbackTimer = setTimeout(() => {
      if (!dataLoaded && !loading && !restoringState) {
        console.log('⏰ Fallback timer: No data loaded, showing empty state');
        // This will trigger the empty state display
      }
    }, 2000); // 2 second fallback

    return () => clearTimeout(fallbackTimer);
  }, [dataLoaded, loading, restoringState]);

  // Set default team when filter options are loaded
  useEffect(() => {
    if (filterOptions.teams && filterOptions.teams.length > 0 && filters.team === 'All') {
      // Look for "Practical Law - Accessibility" team first
      const defaultTeam = filterOptions.teams.find(team => {
        const teamName = typeof team === 'string' ? team : team.name || '';
        return teamName.toLowerCase().includes('practical law') && 
               teamName.toLowerCase().includes('accessibility');
      }) || filterOptions.teams[0]; // Fallback to first team if not found
      
      if (defaultTeam) {
        setFilters(prev => ({
          ...prev,
          team: defaultTeam
        }));
      }
    }
  }, [filterOptions.teams, filters.team]);

  // Auto-update area path when team changes
  useEffect(() => {
    if (filters.team && filters.team !== 'All' && filterOptions.areaPaths && filterOptions.areaPaths.length > 0) {
      // Find area paths that contain the selected team
      const teamAreaPaths = filterOptions.areaPaths.filter(areaPath => 
        areaPath.toLowerCase().includes(filters.team.toLowerCase())
      );
      
      if (teamAreaPaths.length > 0) {
        // If we found specific area paths for this team, use the first one
        // Otherwise, keep "All Areas" to show all areas for this team
        const newAreaPath = teamAreaPaths.length === 1 ? teamAreaPaths[0] : 'All';
        
        if (filters.area_path !== newAreaPath) {
          console.log(`🔄 Auto-updating area path for team "${filters.team}": ${filters.area_path} -> ${newAreaPath}`);
          setFilters(prev => ({
            ...prev,
            area_path: newAreaPath
          }));
        }
      }
    }
  }, [filters.team, filterOptions.areaPaths]);

  // Apply filters whenever filters or workItems change
  useEffect(() => {
    if (dataLoaded) {
      applyFilters();
    }
  }, [workItems, currentFilters, dataLoaded]); // Remove applyFilters from dependencies

  // Save current state to session storage (without large work items data)
  const saveState = useCallback(() => {
    const stateToSave = {
      filters,
      // Don't save workItems and filteredWorkItems to avoid quota exceeded
      // workItems,
      // filteredWorkItems,
      dataLoaded,
      page,
      rowsPerPage,
      workItemsCount: workItems.length, // Save count instead of full data
      filteredCount: filteredWorkItems.length, // Save count instead of full data
      timestamp: Date.now() // Add timestamp for debugging
    };
    console.log('💾 Saving state to session storage:', {
      workItemsCount: workItems.length,
      filteredCount: filteredWorkItems.length,
      dataLoaded,
      timestamp: stateToSave.timestamp
    });
    
    try {
      sessionStorage.setItem('workItemsState', JSON.stringify(stateToSave));
    } catch (error) {
      console.warn('Failed to save state to session storage (quota exceeded):', error);
      // Try to save minimal state
      const minimalState = {
        filters,
        dataLoaded,
        page,
        rowsPerPage,
        timestamp: Date.now()
      };
      try {
        sessionStorage.setItem('workItemsMinimalState', JSON.stringify(minimalState));
        console.log('💾 Saved minimal state instead');
      } catch (minimalError) {
        console.warn('Failed to save even minimal state:', minimalError);
      }
    }
  }, [filters, workItems.length, filteredWorkItems.length, dataLoaded, page, rowsPerPage]);

  // Save state whenever important state changes
  useEffect(() => {
    if (dataLoaded && workItems.length > 0) {
      saveState();
    }
  }, [filters, workItems, dataLoaded, page, rowsPerPage]); // Remove saveState from dependencies

  // Save state when component unmounts (navigating away)
  useEffect(() => {
    return () => {
      if (dataLoaded && workItems.length > 0) {
        console.log('🚪 Component unmounting, saving final state');
        saveState();
      }
    };
  }, [dataLoaded, workItems.length]); // Remove saveState from dependencies

  const loadFilterOptions = async () => {
    try {
      setError('');
      
      // Load only filter options
      const filterOptionsData = await fetchFilterOptions();
      
      setFilterOptions(filterOptionsData || {
        workItemTypes: [],
        states: [],
        assignedTo: [],
        areaPaths: [],
        iterationPaths: [],
        teams: [],
      });
      
    } catch (err) {
      const formattedError = formatApiError(err);
      setError(formattedError.message);
    }
  };

  const loadData = async () => {
    try {
      setLoading(true);
      setError('');
      
      console.log('🔄 Loading work items with filters:', currentFilters);
      
      // Load work items based on current filters
      const workItemsData = await fetchWorkItems(currentFilters);
      
      console.log('📊 Received work items data:', workItemsData?.length || 0, 'items');
      console.log('🎯 Selected team:', currentFilters.team);
      if (workItemsData && workItemsData.length > 0) {
        console.log('📋 Sample work item:', workItemsData[0]);
        console.log('🔍 Sample area path:', workItemsData[0]?.areaPath);
      }
      
      setWorkItems(workItemsData || []);
      setDataLoaded(true);
      
      // Save the new state after loading
      setTimeout(() => {
        saveState();
      }, 100);
      
    } catch (err) {
      const formattedError = formatApiError(err);
      setError(formattedError.message);
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (key, value) => {
    console.log(`🔄 Filter change: ${key} = "${value}"`);
    setFilters(prev => ({
      ...prev,
      [key]: value,
    }));
  };

  const handleClearFilters = () => {
    // Find the default team (Practical Law - Accessibility or first available)
    const defaultTeam = filterOptions.teams?.find(team => {
      const teamName = typeof team === 'string' ? team : team.name || '';
      return teamName.toLowerCase().includes('practical law') && 
             teamName.toLowerCase().includes('accessibility');
    }) || filterOptions.teams?.[0] || 'All';
    
    setFilters({
      search: '',
      team: defaultTeam,
      work_item_type: 'All',
      state: 'All',
      assigned_to: 'All',
      area_path: 'All',
      iteration_path: 'All',
    });
    
    // Clear saved state when filters are cleared
    sessionStorage.removeItem('workItemsState');
  };

  const handleLoadWorkItems = () => {
    loadData();
  };

  const handleAnalyzeWorkItem = (workItemId) => {
    console.log('Analyzing work item:', workItemId, 'onWorkItemSelect:', !!onWorkItemSelect);
    if (onWorkItemSelect) {
      // Find the work item data
      const workItem = workItems.find(item => item.id === workItemId);
      console.log('Found work item:', workItem);
      onWorkItemSelect(workItemId, workItem);
    } else {
      navigate(`/analysis/${workItemId}`);
    }
  };

  const getStateChipColor = (state) => {
    const stateColors = {
      'New': 'info',
      'Active': 'primary',
      'Resolved': 'success',
      'Closed': 'default',
      'Removed': 'error',
    };
    return stateColors[state] || 'default';
  };

  const getTypeChipColor = (type) => {
    const typeColors = {
      'Epic': 'secondary',
      'Feature': 'primary',
      'User Story': 'info',
      'Task': 'success',
      'Bug': 'error',
      'Test Case': 'warning',
    };
    return typeColors[type] || 'default';
  };

  if (!connectionStatus.azure_devops.connected) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Alert severity="warning">
          Please connect to Azure DevOps first to view work items.
        </Alert>
      </Container>
    );
  }

  // Remove the loading state that hides everything - we'll show loading in the table instead

  if (error) {
    return (
      <Container maxWidth="xl" sx={{ py: 3 }}>
        <Alert severity="error" action={
          <Button color="inherit" size="small" onClick={loadData}>
            Retry
          </Button>
        }>
          {error}
        </Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="xl" sx={{ py: hideHeader ? 0 : 3 }}>
      {/* Header - Only show if not hidden */}
      {!hideHeader && (
        <Box sx={{ mb: 3 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Box>
              <Typography variant="h4" component="h1" fontWeight={600}>
                AI-Powered Item Discovery
              </Typography>
              <Typography variant="body1" color="text.secondary" sx={{ mt: 0.5 }}>
                Discover related work items with AI intelligence
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Button
                variant="outlined"
                startIcon={<RefreshIcon />}
                onClick={loadData}
                disabled={loading}
              >
                Refresh
              </Button>
            </Box>
          </Box>

          {/* Stats - Only show if data is loaded */}
          {dataLoaded && (
            <Box sx={{ display: 'flex', gap: 2, mb: 2, flexWrap: 'wrap' }}>
              <Card sx={{ minWidth: 150 }}>
                <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
                  <Typography variant="h6" component="div">
                    {workItems.length}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Total Items
                  </Typography>
                </CardContent>
              </Card>
              <Card sx={{ minWidth: 150 }}>
                <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
                  <Typography variant="h6" component="div">
                    {filteredWorkItems.length}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Filtered Items
                  </Typography>
                </CardContent>
              </Card>
              {filters.team && filters.team !== 'All' && (
                <Card sx={{ minWidth: 200, border: '2px solid', borderColor: 'primary.main' }}>
                  <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
                    <Typography variant="h6" component="div" color="primary">
                      Team Filter Active
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {filters.team}
                    </Typography>
                  </CardContent>
                </Card>
              )}
            </Box>
          )}
        </Box>
      )}

      {/* Action Buttons - Always show even when header is hidden */}


      {/* Work Items Table */}
      <Paper>
        <TableContainer sx={{ maxHeight: 700, overflowX: 'auto' }}>
          <Table stickyHeader>
            <TableHead>
              <TableRow>
                <TableCell sx={{ width: '80px' }}>ID</TableCell>
                <TableCell sx={{ width: '50%', minWidth: '400px' }}>Title</TableCell>
                <TableCell sx={{ width: '100px' }}>Type</TableCell>
                <TableCell sx={{ width: '100px' }}>State</TableCell>
                <TableCell sx={{ width: '200px' }}>Assigned To</TableCell>
                <TableCell align="center" sx={{ width: '200px' }}>Discovery Related Items</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {loading || restoringState ? (
                <TableRow>
                  <TableCell colSpan={6} align="center" sx={{ py: 4 }}>
                    <CircularProgress size={40} sx={{ mb: 2 }} />
                    <Typography variant="h6" color="text.secondary">
                      {restoringState ? 'Restoring previous data...' : 'Discovering work items...'}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {restoringState 
                        ? 'Restoring your previously loaded work items and filters'
                        : 'Please wait while we fetch the data based on your filters'
                      }
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : (
                <>
                  {filteredWorkItems
                    .slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage)
                    .map((item) => (
                      <TableRow 
                        key={item.id} 
                        hover
                        sx={{ 
                          cursor: 'pointer',
                          '& .MuiTableCell-root': {
                            verticalAlign: 'top',
                            paddingTop: 1.5,
                            paddingBottom: 1.5
                          }
                        }}
                        onClick={() => handleAnalyzeWorkItem(item.id)}
                      >
                        <TableCell>
                          <Typography variant="body2" fontWeight={500}>
                            {item.id}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography 
                            variant="body2" 
                            sx={{ 
                              maxWidth: 600,
                              cursor: 'help',
                              display: '-webkit-box',
                              WebkitLineClamp: 2,
                              WebkitBoxOrient: 'vertical',
                              overflow: 'hidden',
                              lineHeight: 1.4,
                              '&:hover': {
                                color: 'primary.main'
                              }
                            }}
                            title={item.title}
                          >
                            {item.title}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={item.type}
                            color={getTypeChipColor(item.type)}
                            size="small"
                            variant="outlined"
                          />
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={item.state}
                            color={getStateChipColor(item.state)}
                            size="small"
                          />
                        </TableCell>
                        <TableCell>
                          <Tooltip title={item.assignedTo || 'Unassigned'} placement="top" arrow>
                            <Typography 
                              variant="body2" 
                              noWrap 
                              sx={{ 
                                maxWidth: 200,
                                cursor: 'help',
                                '&:hover': {
                                  color: 'primary.main'
                                }
                              }}
                            >
                              {item.assignedTo || 'Unassigned'}
                            </Typography>
                          </Tooltip>
                        </TableCell>
                        <TableCell align="center">
                          <Box sx={{ display: 'flex', gap: 0.5, justifyContent: 'center' }}>
                            <Tooltip title="🚀 Launch AI Analysis">
                              <IconButton
                                size="small"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleAnalyzeWorkItem(item.id);
                                }}
                                color="primary"
                              >
                                <AnalysisIcon />
                              </IconButton>
                            </Tooltip>
                          </Box>
                        </TableCell>
                      </TableRow>
                    ))}
                  
                  {filteredWorkItems.length === 0 && !loading && (
                    <TableRow>
                      <TableCell colSpan={7} align="center" sx={{ py: 4 }}>
                        <ViewListIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
                        <Typography variant="h6" color="text.secondary">
                          {!dataLoaded 
                            ? "Select filters and click 'Load Items' to discover work items"
                            : workItems.length === 0 
                              ? "No work items available" 
                              : "No work items match your filters"
                          }
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          {!dataLoaded 
                            ? "Use the filters above to select team, type, and state, then discover work items"
                            : workItems.length === 0 
                              ? "No work items found for the selected criteria" 
                              : "Try adjusting your filters or search terms"
                          }
                        </Typography>
                      </TableCell>
                    </TableRow>
                  )}
                </>
              )}
            </TableBody>
          </Table>
        </TableContainer>
        
        {filteredWorkItems.length > 0 && (
          <TablePagination
            rowsPerPageOptions={[10, 25, 50, 100]}
            component="div"
            count={filteredWorkItems.length}
            rowsPerPage={rowsPerPage}
            page={page}
            onPageChange={(_, newPage) => setPage(newPage)}
            onRowsPerPageChange={(e) => {
              setRowsPerPage(parseInt(e.target.value, 10));
              setPage(0);
            }}
          />
        )}
      </Paper>
    </Container>
  );
};

export default WorkItemsList;

