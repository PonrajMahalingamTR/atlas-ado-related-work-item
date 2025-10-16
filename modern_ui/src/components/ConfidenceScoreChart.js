import React, { useMemo } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Paper,
  LinearProgress,
  Chip,
  Alert,
} from '@mui/material';
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  LineChart,
  Line,
} from 'recharts';
import {
  CheckCircle as CheckCircleIcon,
  Warning as WarningIcon,
  Info as InfoIcon,
  TrendingUp as TrendingUpIcon,
  Assessment as AssessmentIcon,
} from '@mui/icons-material';
import { motion } from 'framer-motion';

const ConfidenceScoreChart = ({ workItems }) => {
  // Debug logging
  console.log('ConfidenceScoreChart - Received workItems:', workItems);
  
  const chartData = useMemo(() => {
    if (!workItems || !Array.isArray(workItems)) {
      return [
        { name: 'High Confidence', value: 0, color: '#4caf50' },
        { name: 'Medium Confidence', value: 0, color: '#ff9800' },
        { name: 'Low Confidence', value: 0, color: '#f44336' },
      ];
    }
    
    // Count confidence levels based on numeric values
    const confidenceCounts = workItems.reduce((acc, item) => {
      const confidence = item.confidence || item.confidenceScore || 0;
      let level;
      
      if (confidence >= 0.8) {
        level = 'high';
      } else if (confidence >= 0.5) {
        level = 'medium';
      } else {
        level = 'low';
      }
      
      acc[level] = (acc[level] || 0) + 1;
      return acc;
    }, {});

    return [
      { name: 'High Confidence', value: confidenceCounts.high || 0, color: '#4caf50' },
      { name: 'Medium Confidence', value: confidenceCounts.medium || 0, color: '#ff9800' },
      { name: 'Low Confidence', value: confidenceCounts.low || 0, color: '#f44336' },
    ];
  }, [workItems]);

  const barChartData = useMemo(() => {
    if (!workItems || !Array.isArray(workItems)) {
      return [];
    }
    
    const stateCounts = workItems.reduce((acc, item) => {
      if (!acc[item.state]) {
        acc[item.state] = { high: 0, medium: 0, low: 0 };
      }
      
      const confidence = item.confidence || item.confidenceScore || 0;
      let level;
      
      if (confidence >= 0.8) {
        level = 'high';
      } else if (confidence >= 0.5) {
        level = 'medium';
      } else {
        level = 'low';
      }
      
      acc[item.state][level]++;
      return acc;
    }, {});

    return Object.entries(stateCounts).map(([state, counts]) => ({
      state,
      high: counts.high,
      medium: counts.medium,
      low: counts.low,
    }));
  }, [workItems]);

  const confidenceDistribution = useMemo(() => {
    const total = workItems.length;
    if (total === 0) return { high: 0, medium: 0, low: 0 };
    
    return {
      high: Math.round(((chartData[0]?.value || 0) / total) * 100),
      medium: Math.round(((chartData[1]?.value || 0) / total) * 100),
      low: Math.round(((chartData[2]?.value || 0) / total) * 100),
    };
  }, [chartData, workItems.length]);

  const getConfidenceIcon = (confidence) => {
    const icons = {
      'high': <CheckCircleIcon color="success" />,
      'medium': <WarningIcon color="warning" />,
      'low': <InfoIcon color="error" />,
    };
    return icons[confidence] || <InfoIcon />;
  };

  const getConfidenceColor = (confidence) => {
    const colors = {
      'high': '#4caf50',
      'medium': '#ff9800',
      'low': '#f44336',
    };
    return colors[confidence] || '#757575';
  };

  if (!workItems || !Array.isArray(workItems) || workItems.length === 0) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="info">
          <Typography variant="h6" gutterBottom>
            No Confidence Data Available
          </Typography>
          <Typography variant="body2">
            There are no related work items to analyze confidence scores for.
          </Typography>
        </Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h5" gutterBottom>
        Confidence Score Analysis
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Visual analysis of AI confidence levels for related work items
      </Typography>

      <Grid container spacing={3}>
        {/* Confidence Distribution Overview */}
        <Grid item xs={12} md={6}>
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5 }}
          >
            <Card elevation={2}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Confidence Distribution
                </Typography>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={chartData}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={120}
                      paddingAngle={5}
                      dataKey="value"
                    >
                      {chartData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </motion.div>
        </Grid>

        {/* Confidence by State */}
        <Grid item xs={12} md={6}>
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5, delay: 0.1 }}
          >
            <Card elevation={2}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Confidence by Work Item State
                </Typography>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={barChartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="state" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="high" stackId="a" fill="#4caf50" name="High" />
                    <Bar dataKey="medium" stackId="a" fill="#ff9800" name="Medium" />
                    <Bar dataKey="low" stackId="a" fill="#f44336" name="Low" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </motion.div>
        </Grid>

        {/* Detailed Confidence Breakdown */}
        <Grid item xs={12}>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            <Card elevation={2}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  Detailed Confidence Analysis
                </Typography>
                
                <Grid container spacing={3}>
                  {/* High Confidence Items */}
                  <Grid item xs={12} md={4}>
                    <Paper elevation={1} sx={{ p: 2, backgroundColor: '#e8f5e8' }}>
                      <Box display="flex" alignItems="center" gap={1} mb={2}>
                        <CheckCircleIcon color="success" />
                        <Typography variant="h6" color="success.main">
                          High Confidence ({chartData[0]?.value || 0})
                        </Typography>
                      </Box>
                      <LinearProgress
                        variant="determinate"
                        value={confidenceDistribution.high}
                        sx={{ height: 8, borderRadius: 4, mb: 1 }}
                        color="success"
                      />
                      <Typography variant="body2" color="text.secondary">
                        {confidenceDistribution.high}% of total items
                      </Typography>
                      <Typography variant="body2" sx={{ mt: 1 }}>
                        These items have strong relationships with the selected work item.
                        High confidence indicates clear functional, technical, or business logic connections.
                      </Typography>
                    </Paper>
                  </Grid>

                  {/* Medium Confidence Items */}
                  <Grid item xs={12} md={4}>
                    <Paper elevation={1} sx={{ p: 2, backgroundColor: '#fff3e0' }}>
                      <Box display="flex" alignItems="center" gap={1} mb={2}>
                        <WarningIcon color="warning" />
                        <Typography variant="h6" color="warning.main">
                          Medium Confidence ({chartData[1]?.value || 0})
                        </Typography>
                      </Box>
                      <LinearProgress
                        variant="determinate"
                        value={confidenceDistribution.medium}
                        sx={{ height: 8, borderRadius: 4, mb: 1 }}
                        color="warning"
                      />
                      <Typography variant="body2" color="text.secondary">
                        {confidenceDistribution.medium}% of total items
                      </Typography>
                      <Typography variant="body2" sx={{ mt: 1 }}>
                        These items have moderate relationships. Review them carefully to determine
                        if they are truly related or if the connection is circumstantial.
                      </Typography>
                    </Paper>
                  </Grid>

                  {/* Low Confidence Items */}
                  <Grid item xs={12} md={4}>
                    <Paper elevation={1} sx={{ p: 2, backgroundColor: '#ffebee' }}>
                      <Box display="flex" alignItems="center" gap={1} mb={2}>
                        <InfoIcon color="error" />
                        <Typography variant="h6" color="error.main">
                          Low Confidence ({chartData[2]?.value || 0})
                        </Typography>
                      </Box>
                      <LinearProgress
                        variant="determinate"
                        value={confidenceDistribution.low}
                        sx={{ height: 8, borderRadius: 4, mb: 1 }}
                        color="error"
                      />
                      <Typography variant="body2" color="text.secondary">
                        {confidenceDistribution.low}% of total items
                      </Typography>
                      <Typography variant="body2" sx={{ mt: 1 }}>
                        These items have weak relationships. They may be tangentially related
                        or the AI may have identified a potential connection that needs verification.
                      </Typography>
                    </Paper>
                  </Grid>
                </Grid>
              </CardContent>
            </Card>
          </motion.div>
        </Grid>

      </Grid>
    </Box>
  );
};

export default ConfidenceScoreChart;
