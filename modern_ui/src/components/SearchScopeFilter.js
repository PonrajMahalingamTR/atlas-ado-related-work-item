import React, { useState, useMemo } from 'react';
import {
  Box,
  Paper,
  Typography,
  FormControl,
  FormLabel,
  RadioGroup,
  FormControlLabel,
  Radio,
  Chip,
  // Tooltip, // DISABLED: Not used
  // Alert, // DISABLED: Not used
  Button,
  CircularProgress,
  Select,
  MenuItem,
  OutlinedInput,
  Checkbox,
  ListItemText,
  Divider,
  Grid,
  IconButton,
} from '@mui/material';
import {
  GpsFixed as LaserFocusIcon,
  Balance as BalancedSearchIcon,
  Psychology as AIDeepDiveIcon,
  Info as InfoIcon,
  Refresh as RefreshIcon,
  CalendarToday as DateIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Psychology as AIIcon,
} from '@mui/icons-material';

const SearchScopeFilter = ({ 
  searchScope, 
  onScopeChange, 
  selectedTeam, 
  teamGroup, 
  totalTeams,
  onReRunSearch,
  isSearching = false,
  dateFilter = 'last-month',
  onDateFilterChange,
  workItemTypes = ['User Story', 'Task', 'Bug', 'Feature', 'Epic'],
  onWorkItemTypesChange,
  availableWorkItemTypes = ['User Story', 'Task', 'Bug', 'Epic', 'Feature', 'Test Case', 'Issue', 'Change Request'],
  groupTeams = [],
  selectedGroupTeams = [],
  onGroupTeamsChange,
  allTeams = [],
  selectedAllTeams = [],
  onAllTeamsChange,
  loading = false,
  refinedWorkItems = [],
  onUnleashAI,
  runningAnalysis = false,
  openArenaLoading = false
}) => {
  const [filtersExpanded, setFiltersExpanded] = useState(false);
  const dateFilterOptions = [
    { value: 'current-iteration', label: 'Current Iteration' },
    { value: 'previous-iteration', label: 'Previous Iteration' },
    { value: 'last-2-iterations', label: 'Last 2 Iterations' },
    { value: 'last-month', label: 'Last Month' },
    { value: 'last-2-months', label: 'Last 2 Months' },
    { value: 'current-quarter', label: 'Current Quarter' },
    { value: 'previous-quarter', label: 'Previous Quarter' },
    { value: 'last-3-quarters', label: 'Last 3 Quarters' },
    { value: '1-year', label: '1 Year' },
    { value: '2-years', label: '2 Years' },
    { value: '3-years', label: '3 Years' },
    { value: '4-years', label: '4 Years' },
    { value: '5-years', label: '5 Years' },
  ];

  // Dynamically calculate team group from selected team name
  const dynamicTeamGroup = useMemo(() => {
    if (!selectedTeam) return null;
    
    // Handle both string and object formats for team data
    const teamName = typeof selectedTeam === 'string' ? selectedTeam : selectedTeam.name || '';
    if (!teamName) return null;
    
    // More robust team group extraction
    const teamNameLower = teamName.toLowerCase();
    
    // Check for specific patterns
    if (teamNameLower.includes('accessibility') || teamNameLower.includes('a11y')) {
      return 'Accessibility';
    }
    
    // Fallback: try to extract from common patterns
    // Pattern 1: "Something - Group" -> "Group"
    const dashParts = teamName.split(' - ');
    if (dashParts.length >= 2) {
      return dashParts[dashParts.length - 1];
    }
    
    // Pattern 2: "Something Group" -> "Group" (for cases like "WLUS Accessibility")
    const words = teamName.split(' ');
    if (words.length >= 2) {
      return words[words.length - 1];
    }
    
    return null;
  }, [selectedTeam]);

  // Count teams in the dynamic team group
  // DISABLED: Dynamic team group count - not used and causes unnecessary calculations
  // const dynamicTeamGroupCount = useMemo(() => {
  //   if (!dynamicTeamGroup || !groupTeams.length) return 0;
  //   
  //   // Count teams that belong to the same group using the same logic
  //   return groupTeams.filter(team => {
  //     // Handle both string and object formats for team data
  //     const teamName = typeof team === 'string' ? team : team.name || '';
  //     if (!teamName) return false;
  //     
  //     const teamNameLower = teamName.toLowerCase();
  //     
  //     // Apply the same group identification logic
  //     if (dynamicTeamGroup === 'Accessibility') {
  //       return teamNameLower.includes('accessibility') || teamNameLower.includes('a11y');
  //     }
  //     
  //     // For other groups, use the same extraction logic
  //     const dashParts = teamName.split(' - ');
  //     if (dashParts.length >= 2) {
  //       return dashParts[dashParts.length - 1] === dynamicTeamGroup;
  //     }
  //     
  //     const words = teamName.split(' ');
  //     if (words.length >= 2) {
  //       return words[words.length - 1] === dynamicTeamGroup;
  //     }
  //     
  //     return false;
  //   }).length;
  // }, [dynamicTeamGroup, groupTeams]);

  const scopeOptions = [
    {
      value: 'generic',
      label: '🧠 AI Deep Dive',
      description: 'Azure DevOps → AI Embeddings → Vector Database → LLM Analysis',
      icon: <AIDeepDiveIcon />,
      color: 'default',
      tooltip: 'Full AI intelligence stack with embeddings and vector database for maximum accuracy.'
    },
    {
      value: 'balanced',
      label: '⚡ Balanced Search',
      description: 'Azure DevOps → LLM Analysis',
      icon: <BalancedSearchIcon />,
      color: 'secondary',
      tooltip: 'Smart AI analysis with balanced scope and precision for optimal results.'
    },
    {
      value: 'specific',
      label: '🎯 Laser Focus',
      description: 'Azure DevOps',
      icon: <LaserFocusIcon />,
      color: 'primary',
      tooltip: 'Direct AI-powered search for focused and targeted results.'
    }
  ];

  return (
    <Paper elevation={1} sx={{ p: 3, mb: 2 }}>
      <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
        <Box display="flex" alignItems="center">
          <Typography variant="h6" sx={{ mr: 1 }}>
            ⚡ Analysis Strategies
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <IconButton
            onClick={() => setFiltersExpanded(!filtersExpanded)}
            aria-label="expand additional filters"
            size="small"
          >
            {filtersExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
          </IconButton>
        </Box>
      </Box>



      <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2 }}>
        <FormControl component="fieldset" sx={{ flex: 1 }}>
          <RadioGroup
            value={searchScope}
            onChange={(e) => {
              const newScope = e.target.value;
              console.log('🔄 Search scope changed to:', newScope);
              onScopeChange(newScope);
              // Don't auto-trigger search - let user control when to search
              console.log('ℹ️ Scope updated, search will happen when user clicks "Unleash AI Intelligence"');
            }}
            sx={{ gap: 1, flexDirection: 'row', flexWrap: 'wrap' }}
          >
            {scopeOptions.map((option) => (
              <FormControlLabel
                key={option.value}
                value={option.value}
                control={<Radio color={option.color} sx={{ display: 'none' }} />}
                label={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, minWidth: 200 }}>
                    <Box>
                      <Typography variant="body2" fontWeight="medium">
                        {option.label}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {option.description}
                      </Typography>
                    </Box>
                  </Box>
                }
                sx={{
                  border: searchScope === option.value ? `2px solid` : '1px solid',
                  borderColor: searchScope === option.value ? 
                    `${option.color}.main` : 'divider',
                  borderRadius: 1,
                  p: 1,
                  m: 0,
                  '&:hover': {
                    backgroundColor: 'action.hover',
                  },
                  transition: 'all 0.2s ease-in-out',
                }}
              />
            ))}
          </RadioGroup>
        </FormControl>
        
         {/* Unleash AI Intelligence Button - Hidden for Laser Focus */}
         {searchScope !== 'specific' && (
           <Box sx={{ display: 'flex', alignItems: 'center', minWidth: 200 }}>
             <Button
               variant="contained"
               size="large"
               startIcon={<AIIcon />}
               onClick={onUnleashAI}
               disabled={runningAnalysis || openArenaLoading}
               sx={{ 
                 minWidth: 200,
                 py: 1.5,
                 fontSize: '1.1rem',
                 fontWeight: 'bold',
                 borderRadius: 2,
                 boxShadow: 3,
                 background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                 color: 'white',
                 '&:hover': {
                   background: 'linear-gradient(135deg, #5a6fd8 0%, #6a4190 100%)',
                   boxShadow: 6,
                   transform: 'translateY(-2px)',
                 },
                 '&.Mui-disabled': {
                   background: 'rgba(0,0,0,0.12)',
                   color: 'rgba(0,0,0,0.26)',
                 },
                 transition: 'all 0.3s ease'
               }}
             >
               {runningAnalysis || openArenaLoading ? 'Unleashing AI Intelligence...' : 'Unleash AI Intelligence'}
             </Button>
           </Box>
         )}
      </Box>

      {/* Strategy Information - Subtle addition */}
      <Box sx={{ 
        mt: 2, 
        display: 'flex',
        alignItems: 'flex-start',
        gap: 1
      }}>
        <InfoIcon sx={{ 
          color: 'text.secondary', 
          fontSize: 18, 
          mt: 0.2,
          flexShrink: 0
        }} />
        <Typography variant="body2" sx={{ 
          color: 'text.secondary',
          fontStyle: 'italic',
          textAlign: 'left',
          lineHeight: 1.5
        }}>
          {searchScope === 'generic' ? 
            'Utilizes advanced semantic similarity techniques and multiple LLMs to uncover hidden work item connections through deep contextual understanding.' :
           searchScope === 'specific' ? 
            'Leverages direct Azure DevOps APIs for instant, cost-free insights—ideal for quick lookups with minimal compute.' :
            'Combines enhanced DevOps metadata with large language models to perform intelligent cross-team searches and generate confidence scores.'}
        </Typography>
      </Box>

      {/* Additional Filters - Only show when expanded */}
      {filtersExpanded && (
        <>
          <Divider sx={{ my: 2 }} />
          
          <Box sx={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: 1, 
            mb: 3,
            p: 2,
            backgroundColor: 'grey.50',
            borderRadius: 1,
            border: '1px solid',
            borderColor: 'grey.300'
          }}>
            <Typography 
              variant="h6" 
              sx={{ 
                display: 'flex', 
                alignItems: 'center', 
                gap: 1,
                color: 'text.primary',
                fontWeight: 'bold'
              }}
            >
              <DateIcon />
              Additional Filters
            </Typography>
          </Box>

          {/* Team Selection for Specific Scope */}
          {searchScope === 'specific' && groupTeams.length > 0 && (
            <>
              <Typography variant="h6" sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
                <BalancedSearchIcon />
                Select Teams from '{teamGroup}' Group
              </Typography>
              
              <FormControl fullWidth sx={{ mb: 3 }}>
                <FormLabel component="legend" sx={{ mb: 1, fontWeight: 'bold' }}>
                  Choose which teams to include in the search:
                </FormLabel>
                <Select
                  multiple
                  value={selectedGroupTeams}
                  onChange={(e) => onGroupTeamsChange && onGroupTeamsChange(e.target.value)}
                  input={<OutlinedInput />}
                  renderValue={(selected) => (
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                      {selected.map((team) => (
                        <Chip key={typeof team === 'string' ? team : team.id || team.name} label={typeof team === 'string' ? team : team.name || 'Unknown Team'} size="small" />
                      ))}
                    </Box>
                  )}
                >
                  {groupTeams.map((team) => (
                    <MenuItem key={typeof team === 'string' ? team : team.id || team.name} value={team}>
                      <Checkbox checked={selectedGroupTeams.indexOf(team) > -1} />
                      <ListItemText primary={typeof team === 'string' ? team : team.name || 'Unknown Team'} />
                    </MenuItem>
                  ))}
                </Select>
                <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                  {selectedGroupTeams.length === 0 
                    ? `All ${groupTeams.length} teams in the '${teamGroup}' group will be searched by default`
                    : `${selectedGroupTeams.length} of ${groupTeams.length} teams selected`
                  }
                </Typography>
              </FormControl>
            </>
          )}

          {/* Team Selection for Generic Scope */}
          {searchScope === 'generic' && allTeams.length > 0 && (
            <>
              <Typography variant="h6" sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
                <AIDeepDiveIcon />
                Select Teams from All Project Teams
              </Typography>
              
              <FormControl fullWidth sx={{ mb: 3 }}>
                <FormLabel component="legend" sx={{ mb: 1, fontWeight: 'bold' }}>
                  Choose which teams to include in the search:
                </FormLabel>
                <Select
                  multiple
                  value={selectedAllTeams}
                  onChange={(e) => onAllTeamsChange && onAllTeamsChange(e.target.value)}
                  input={<OutlinedInput />}
                  renderValue={(selected) => (
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                      {selected.map((team) => (
                        <Chip key={typeof team === 'string' ? team : team.id || team.name} label={typeof team === 'string' ? team : team.name || 'Unknown Team'} size="small" />
                      ))}
                    </Box>
                  )}
                >
                  {allTeams.map((team) => (
                    <MenuItem key={typeof team === 'string' ? team : team.id || team.name} value={team}>
                      <Checkbox checked={selectedAllTeams.indexOf(team) > -1} />
                      <ListItemText primary={typeof team === 'string' ? team : team.name || 'Unknown Team'} />
                    </MenuItem>
                  ))}
                </Select>
                <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                  {selectedAllTeams.length === 0 
                    ? `All ${allTeams.length} teams in the project will be searched by default`
                    : `${selectedAllTeams.length} of ${allTeams.length} teams selected`
                  }
                </Typography>
              </FormControl>
            </>
          )}

        <Grid container spacing={2} alignItems="center" justifyContent="center">
          {/* Date Filter */}
          <Grid item xs={12} md={4}>
            <FormControl fullWidth>
              <FormLabel component="legend" sx={{ mb: 1, fontWeight: 'bold' }}>
                Date Range Filter
              </FormLabel>
              <Select
                value={dateFilter}
                onChange={(e) => onDateFilterChange && onDateFilterChange(e.target.value)}
                input={<OutlinedInput />}
                displayEmpty
              >
                {dateFilterOptions.map((option) => (
                  <MenuItem key={option.value} value={option.value}>
                    {option.label}
                  </MenuItem>
                ))}
              </Select>
              <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                Filter work items by creation date
              </Typography>
            </FormControl>
          </Grid>

          {/* Work Item Type Filter */}
          <Grid item xs={12} md={4}>
            <FormControl fullWidth>
              <FormLabel component="legend" sx={{ mb: 1, fontWeight: 'bold' }}>
                Work Item Types
              </FormLabel>
              <Select
                multiple
                value={workItemTypes}
                onChange={(e) => onWorkItemTypesChange && onWorkItemTypesChange(e.target.value)}
                input={<OutlinedInput />}
                renderValue={(selected) => (
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                    {selected.map((value) => (
                      <Chip key={value} label={value} size="small" />
                    ))}
                  </Box>
                )}
              >
                {availableWorkItemTypes.map((type) => (
                  <MenuItem key={type} value={type}>
                    <Checkbox checked={workItemTypes.indexOf(type) > -1} />
                    <ListItemText primary={type} />
                  </MenuItem>
                ))}
              </Select>
              <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                Select work item types to include in search
              </Typography>
            </FormControl>
          </Grid>

          {/* Apply Additional Filters Button */}
          <Grid item xs={12} md={4} sx={{ display: 'flex', justifyContent: 'center' }}>
            <Button
              variant="outlined"
              startIcon={isSearching ? <CircularProgress size={20} /> : <RefreshIcon />}
              onClick={onReRunSearch}
              disabled={isSearching}
              size="large"
              sx={{ 
                height: '56px',
                minWidth: '200px',
                maxWidth: '250px',
                width: 'fit-content'
              }}
            >
              {isSearching ? 'Applying Filters...' : 'Apply Additional Filters'}
            </Button>
          </Grid>
        </Grid>
        </>
      )}
    </Paper>
  );
};

export default SearchScopeFilter;
