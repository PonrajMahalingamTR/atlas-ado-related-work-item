import React from 'react';
import {
  Box,
  Typography,
  Chip,
  Paper,
  Stepper,
  Step,
  StepLabel,
  StepContent,
  Avatar,
  Alert,
  Grid,
  Link,
} from '@mui/material';
import {
  Work as WorkIcon,
  Timeline as TimelineIcon,
  Assessment as AssessmentIcon,
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon,
  Info as InfoIcon,
  OpenInNew as OpenInNewIcon,
} from '@mui/icons-material';

const WorkItemHierarchy = ({ hierarchy, selectedWorkItem }) => {
  // Debug logging
  console.log('WorkItemHierarchy - Received hierarchy:', hierarchy);
  console.log('WorkItemHierarchy - Hierarchy length:', hierarchy?.length);
  console.log('WorkItemHierarchy - Selected work item:', selectedWorkItem);
  
  // Generate Azure DevOps URL for a work item
  const getAzureDevOpsUrl = (workItemId) => {
    return `https://dev.azure.com/your-organization/your-project/_workitems/edit/${workItemId}`;
  };

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

  const getWorkItemTypeIcon = (type) => {
    const typeIcons = {
      'Epic': <AssessmentIcon />,
      'Feature': <TimelineIcon />,
      'User Story': <WorkIcon />,
      'Task': <WorkIcon />,
      'Bug': <WarningIcon />,
    };
    return typeIcons[type] || <WorkIcon />;
  };

  const getWorkItemTypeColor = (type) => {
    const typeColors = {
      'Epic': '#9c27b0',
      'Feature': '#ff9800',
      'User Story': '#2196f3',
      'Task': '#4caf50',
      'Bug': '#f44336',
    };
    return typeColors[type] || '#757575';
  };

  if (!hierarchy || hierarchy.length === 0) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="info">
          <Typography variant="h6" gutterBottom>
            No Hierarchy Information Available
          </Typography>
          <Typography variant="body2">
            The selected work item does not have hierarchical relationships or 
            the hierarchy information could not be retrieved.
          </Typography>
        </Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h5" gutterBottom>
        Work Item Hierarchy
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Hierarchical structure showing the relationship between work items from root to the selected item
      </Typography>

      <Paper elevation={2} sx={{ p: 3 }}>
        <Stepper orientation="vertical" activeStep={hierarchy.length - 1}>
          {hierarchy.map((item, index) => (
            <Step key={item.id} completed={index < hierarchy.length - 1}>
              <StepLabel
                StepIconComponent={({ active, completed }) => (
                  <Avatar
                    sx={{
                      bgcolor: completed 
                        ? getWorkItemTypeColor(item.type) 
                        : active 
                          ? getWorkItemTypeColor(item.type)
                          : 'grey.300',
                      width: 40,
                      height: 40,
                    }}
                  >
                    {getWorkItemTypeIcon(item.type)}
                  </Avatar>
                )}
              >
                <Box display="flex" alignItems="center" gap={2}>
                  <Box>
                    {index === 0 && (
                      <Typography variant="caption" color="primary" sx={{ fontWeight: 'bold', display: 'block' }}>
                        Parent Epic
                      </Typography>
                    )}
                    {index === 1 && (
                      <Typography variant="caption" color="primary" sx={{ fontWeight: 'bold', display: 'block' }}>
                        Parent Feature
                      </Typography>
                    )}
                    <Link
                      href={getAzureDevOpsUrl(item.id)}
                      target="_blank"
                      rel="noopener noreferrer"
                      sx={{ 
                        textDecoration: 'none',
                        color: 'inherit',
                        '&:hover': {
                          textDecoration: 'underline',
                          color: 'primary.main',
                        }
                      }}
                    >
                      <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        #{item.id} - {item.title}
                        <OpenInNewIcon fontSize="small" />
                      </Typography>
                    </Link>
                  </Box>
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
                  <Chip
                    label={item.type}
                    size="small"
                    sx={{
                      backgroundColor: getWorkItemTypeColor(item.type),
                      color: 'white',
                    }}
                  />
                </Box>
              </StepLabel>
              <StepContent>
                <Box sx={{ ml: 4, mb: 2 }}>
                  <Paper elevation={1} sx={{ p: 2, backgroundColor: 'grey.50' }}>
                    <Grid container spacing={2}>
                      <Grid item xs={12} md={6}>
                        <Typography variant="subtitle2" gutterBottom>
                          Work Item Details
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          <strong>ID:</strong> {item.id}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          <strong>Type:</strong> {item.type}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          <strong>State:</strong> {item.state}
                        </Typography>
                        {item.assignedTo && (
                          <Typography variant="body2" color="text.secondary">
                            <strong>Assigned to:</strong> {item.assignedTo}
                          </Typography>
                        )}
                      </Grid>
                      <Grid item xs={12} md={6}>
                        <Typography variant="subtitle2" gutterBottom>
                          Additional Information
                        </Typography>
                        {item.areaPath && (
                          <Typography variant="body2" color="text.secondary">
                            <strong>Area Path:</strong> {item.areaPath}
                          </Typography>
                        )}
                        {item.iterationPath && (
                          <Typography variant="body2" color="text.secondary">
                            <strong>Iteration Path:</strong> {item.iterationPath}
                          </Typography>
                        )}
                        {item.reason && (
                          <Typography variant="body2" color="text.secondary">
                            <strong>Reason:</strong> {item.reason}
                          </Typography>
                        )}
                      </Grid>
                    </Grid>
                  </Paper>
                </Box>
              </StepContent>
            </Step>
          ))}
        </Stepper>
      </Paper>

    </Box>
  );
};

export default WorkItemHierarchy;
