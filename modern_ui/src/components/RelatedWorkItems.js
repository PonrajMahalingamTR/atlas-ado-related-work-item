import React, { useState, useMemo } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Chip,
  Grid,
  Paper,
  IconButton,
  Tooltip,
  Badge,
  Avatar,
  Button,
  TextField,
  InputAdornment,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Stack,
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  ListItemSecondaryAction,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Alert,
  LinearProgress,
} from '@mui/material';
import {
  Search as SearchIcon,
  FilterList as FilterListIcon,
  Sort as SortIcon,
  ExpandMore as ExpandMoreIcon,
  Work as WorkIcon,
  Timeline as TimelineIcon,
  Assessment as AssessmentIcon,
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon,
  Info as InfoIcon,
  ArrowForward as ArrowForwardIcon,
  OpenInNew as OpenInNewIcon,
  Star as StarIcon,
  StarBorder as StarBorderIcon,
} from '@mui/icons-material';
import { motion, AnimatePresence } from 'framer-motion';

const RelatedWorkItems = ({ workItems, selectedWorkItem }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [sortBy, setSortBy] = useState('createdDate');
  const [filterByType, setFilterByType] = useState('all');
  const [expandedItems, setExpandedItems] = useState({});

  const filteredAndSortedItems = useMemo(() => {
    if (!workItems || workItems.length === 0) {
      return [];
    }
    
    let filtered = workItems;

    // Filter by search term
    if (searchTerm) {
      filtered = filtered.filter(item =>
        item.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
        item.id.toString().includes(searchTerm) ||
        item.description?.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    // Filter by work item type
    if (filterByType !== 'all') {
      filtered = filtered.filter(item => item.type === filterByType);
    }

    // Sort items
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'title':
          return a.title.localeCompare(b.title);
        case 'state':
          return a.state.localeCompare(b.state);
        case 'type':
          return a.type.localeCompare(b.type);
        case 'assignedTo':
          return (a.assignedTo || 'Unassigned').localeCompare(b.assignedTo || 'Unassigned');
        case 'createdDate':
          return new Date(b.createdDate) - new Date(a.createdDate);
        case 'id':
          return b.id - a.id;
        default:
          return new Date(b.createdDate) - new Date(a.createdDate);
      }
    });

    return filtered;
  }, [workItems, searchTerm, sortBy, filterByType]);


  const getStateColor = (state) => {
    const stateColors = {
      'New': '#757575',
      'Active': '#1976d2',
      'Resolved': '#388e3c',
      'Closed': '#2e7d32',
      'Removed': '#d32f2f',
    };
    return stateColors[state] || '#757575';
  };

  const getStateIcon = (state) => {
    const stateIcons = {
      'New': <InfoIcon />,
      'Active': <WorkIcon />,
      'Resolved': <CheckCircleIcon />,
      'Closed': <CheckCircleIcon />,
      'Removed': <WarningIcon />,
    };
    return stateIcons[state] || <InfoIcon />;
  };

  const getRelationshipTypeColor = (type) => {
    const colors = {
      'dependency': '#2196f3',
      'feature': '#4caf50',
      'bug': '#f44336',
      'enhancement': '#ff9800',
      'blocking': '#9c27b0',
    };
    return colors[type] || '#757575';
  };

  const toggleExpanded = (itemId) => {
    setExpandedItems(prev => ({
      ...prev,
      [itemId]: !prev[itemId]
    }));
  };

  const workItemTypeStats = useMemo(() => {
    if (!workItems || workItems.length === 0) {
      return {};
    }
    
    const stats = workItems.reduce((acc, item) => {
      if (item.type) {
        acc[item.type] = (acc[item.type] || 0) + 1;
      }
      return acc;
    }, {});
    return stats;
  }, [workItems]);

  return (
    <Box sx={{ p: 2 }}>
      {/* Header with Stats */}

      {/* Filters and Search */}
      <Paper elevation={1} sx={{ p: 2, mb: 2 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} md={4}>
            <TextField
              fullWidth
              placeholder="Search work items..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
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
          <Grid item xs={12} md={3}>
            <FormControl fullWidth size="small">
              <InputLabel>Filter by Type</InputLabel>
              <Select
                value={filterByType}
                onChange={(e) => setFilterByType(e.target.value)}
                label="Filter by Type"
              >
                <MenuItem value="all">All Types</MenuItem>
                <MenuItem value="User Story">User Story</MenuItem>
                <MenuItem value="Task">Task</MenuItem>
                <MenuItem value="Bug">Bug</MenuItem>
                <MenuItem value="Epic">Epic</MenuItem>
                <MenuItem value="Feature">Feature</MenuItem>
                <MenuItem value="Test Case">Test Case</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} md={3}>
            <FormControl fullWidth size="small">
              <InputLabel>Sort by</InputLabel>
              <Select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                label="Sort by"
              >
                <MenuItem value="createdDate">Created Date</MenuItem>
                <MenuItem value="title">Title</MenuItem>
                <MenuItem value="state">State</MenuItem>
                <MenuItem value="type">Type</MenuItem>
                <MenuItem value="assignedTo">Assigned To</MenuItem>
                <MenuItem value="id">Work Item ID</MenuItem>
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={12} md={2}>
            <Button
              fullWidth
              variant="outlined"
              startIcon={<FilterListIcon />}
              onClick={() => {
                setSearchTerm('');
                setFilterByType('all');
                setSortBy('createdDate');
              }}
            >
              Clear Filters
            </Button>
          </Grid>
        </Grid>
      </Paper>

      {/* Work Items List */}
      <Box>
        <AnimatePresence>
          {filteredAndSortedItems.map((item, index) => (
            <motion.div
              key={item.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3, delay: index * 0.05 }}
            >
              <Card 
                elevation={2} 
                sx={{ 
                  mb: 2, 
                  borderLeft: `4px solid ${getStateColor(item.state)}`,
                  '&:hover': {
                    elevation: 4,
                    transform: 'translateY(-2px)',
                    transition: 'all 0.2s ease-in-out',
                  }
                }}
              >
                <CardContent>
                  <Box display="flex" alignItems="flex-start" justifyContent="space-between">
                    <Box flex={1}>
                      <Box display="flex" alignItems="center" gap={2} mb={1}>
                        <Typography variant="h6" component="div">
                          #{item.id}
                        </Typography>
                        <Chip
                          label={item.type}
                          size="small"
                          color="primary"
                          variant="outlined"
                        />
                        <Chip
                          icon={getStateIcon(item.state)}
                          label={item.state}
                          size="small"
                          variant="outlined"
                          sx={{ 
                            borderColor: getStateColor(item.state),
                            color: getStateColor(item.state),
                          }}
                        />
                        {item.priority && (
                          <Chip
                            label={`Priority: ${item.priority}`}
                            size="small"
                            variant="outlined"
                            color={item.priority === '1' ? 'error' : item.priority === '2' ? 'warning' : 'default'}
                          />
                        )}
                      </Box>
                      
                      <Typography variant="h6" gutterBottom sx={{ mb: 1 }}>
                        {item.title}
                      </Typography>

                      <Grid container spacing={1} sx={{ mt: 1 }}>
                        <Grid item xs={12} sm={6}>
                          <Typography variant="body2" color="text.secondary">
                            <strong>Assigned to:</strong> {item.assignedTo || 'Unassigned'}
                          </Typography>
                        </Grid>
                        <Grid item xs={12} sm={6}>
                          <Typography variant="body2" color="text.secondary">
                            <strong>Created:</strong> {item.createdDate ? new Date(item.createdDate).toLocaleDateString() : 'N/A'}
                          </Typography>
                        </Grid>
                        <Grid item xs={12}>
                          <Typography variant="body2" color="text.secondary">
                            <strong>Area:</strong> {item.areaPath || 'N/A'}
                          </Typography>
                        </Grid>
                        <Grid item xs={12}>
                          <Typography variant="body2" color="text.secondary">
                            <strong>Iteration:</strong> {item.iterationPath || 'N/A'}
                          </Typography>
                        </Grid>
                        {item.tags && (
                          <Grid item xs={12}>
                            <Typography variant="body2" color="text.secondary">
                              <strong>Tags:</strong> {item.tags}
                            </Typography>
                          </Grid>
                        )}
                      </Grid>

                    </Box>

                    <Box display="flex" flexDirection="column" gap={1}>
                      <Tooltip title="View in Azure DevOps">
                        <IconButton 
                          size="small"
                          onClick={() => window.open(`https://dev.azure.com/your-organization/your-project/_workitems/edit/${item.id}`, '_blank')}
                        >
                          <OpenInNewIcon />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Add to Favorites">
                        <IconButton size="small">
                          <StarBorderIcon />
                        </IconButton>
                      </Tooltip>
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </AnimatePresence>

        {filteredAndSortedItems.length === 0 && (
          <Paper elevation={1} sx={{ p: 4, textAlign: 'center' }}>
            <Typography variant="h6" color="text.secondary" gutterBottom>
              No work items found
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Try adjusting your search criteria or filters
            </Typography>
          </Paper>
        )}
      </Box>
    </Box>
  );
};

export default RelatedWorkItems;
