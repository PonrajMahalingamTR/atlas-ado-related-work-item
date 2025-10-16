import React, { useState } from 'react';
import {
  Box,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Typography,
  Paper,
  Divider,
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
} from '@mui/icons-material';

import WorkItemHierarchy from './WorkItemHierarchy';
import ConfidenceScoreChart from './ConfidenceScoreChart';
import AnalysisInsights from './AnalysisInsights';
import PowerMatchesSection from './PowerMatchesSection';

const CombinedAnalysisTab = ({ 
  hierarchy, 
  hierarchyLoading,
  workItems, 
  confidenceBreakdown, 
  chartData,
  insights,
  selectedWorkItem,
  onWorkItemSelect 
}) => {
  // Debug logging
  console.log('CombinedAnalysisTab - Received hierarchy:', hierarchy);
  console.log('CombinedAnalysisTab - Hierarchy loading:', hierarchyLoading);
  console.log('CombinedAnalysisTab - Hierarchy length:', hierarchy?.length);
  const [expandedSections, setExpandedSections] = useState({
    powerMatches: true,
    insights: false,
    confidence: false,
    hierarchy: false
  });

  const handleSectionChange = (section) => (event, isExpanded) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: isExpanded
    }));
  };

  // Dynamic title function for Power Matches section
  const getDynamicPowerMatchesTitle = () => {
    const titles = [
      '🏆 Top AI Champions',
      '⭐ Premium Matches',
      '🎯 Strong AI Connections',
      '💎 High-Value Discoveries',
      '🚀 Power Matches',
      '🔥 Hot AI Picks',
      '✨ Perfect AI Finds',
      '💪 Strong AI Reasoning',
      '🎪 AI Magic Results',
      '🧠 Smart AI Selections',
      '⚡ Lightning AI Matches',
      '🌟 Star AI Picks',
      '🏅 AI Gold Standards',
      '💫 AI Excellence',
      '🎭 AI Masterpieces',
      '🔮 AI Predictions'
    ];
    return titles[Math.floor(Math.random() * titles.length)];
  };

  return (
    <Box sx={{ p: 2 }}>

      {/* Power Matches Section */}
      <Accordion 
        expanded={expandedSections.powerMatches} 
        onChange={handleSectionChange('powerMatches')}
        sx={{ mb: 2, boxShadow: 2 }}
      >
        <AccordionSummary
          expandIcon={<ExpandMoreIcon />}
          sx={{ 
            background: 'linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%)', 
            color: 'white',
            '&:hover': { background: 'linear-gradient(135deg, #ff5252 0%, #e74c3c 100%)' }
          }}
        >
          <Typography variant="h6" sx={{ fontWeight: 'bold' }}>
            {getDynamicPowerMatchesTitle()}
          </Typography>
        </AccordionSummary>
        <AccordionDetails sx={{ p: 0 }}>
          <PowerMatchesSection workItems={workItems} />
        </AccordionDetails>
      </Accordion>

      {/* Smart Recommendations Section */}
      <Accordion 
        expanded={expandedSections.insights} 
        onChange={handleSectionChange('insights')}
        sx={{ mb: 2, boxShadow: 2 }}
      >
        <AccordionSummary
          expandIcon={<ExpandMoreIcon />}
          sx={{ 
            backgroundColor: 'success.light', 
            color: 'white',
            '&:hover': { backgroundColor: 'success.main' }
          }}
        >
          <Typography variant="h6" sx={{ fontWeight: 'bold' }}>
            💡 Smart Recommendations
          </Typography>
        </AccordionSummary>
        <AccordionDetails sx={{ p: 0 }}>
          <AnalysisInsights 
            insights={insights}
            selectedWorkItem={selectedWorkItem}
            onWorkItemSelect={onWorkItemSelect}
          />
        </AccordionDetails>
      </Accordion>

      {/* AI Confidence Metrics Section */}
      <Accordion 
        expanded={expandedSections.confidence} 
        onChange={handleSectionChange('confidence')}
        sx={{ mb: 2, boxShadow: 2 }}
      >
        <AccordionSummary
          expandIcon={<ExpandMoreIcon />}
          sx={{ 
            backgroundColor: 'secondary.light', 
            color: 'white',
            '&:hover': { backgroundColor: 'secondary.main' }
          }}
        >
          <Typography variant="h6" sx={{ fontWeight: 'bold' }}>
            📈 AI Confidence Metrics
          </Typography>
        </AccordionSummary>
        <AccordionDetails sx={{ p: 0 }}>
          <ConfidenceScoreChart 
            workItems={workItems}
            confidenceBreakdown={confidenceBreakdown}
            chartData={chartData}
          />
        </AccordionDetails>
      </Accordion>

      {/* Work Item Tree Section */}
      <Accordion 
        expanded={expandedSections.hierarchy} 
        onChange={handleSectionChange('hierarchy')}
        sx={{ mb: 2, boxShadow: 2 }}
      >
        <AccordionSummary
          expandIcon={<ExpandMoreIcon />}
          sx={{ 
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', 
            color: 'white',
            '&:hover': { background: 'linear-gradient(135deg, #5a6fd8 0%, #6a4190 100%)' }
          }}
        >
          <Typography variant="h6" sx={{ fontWeight: 'bold' }}>
            📊 Work Item Tree
          </Typography>
        </AccordionSummary>
        <AccordionDetails sx={{ p: 0 }}>
          <WorkItemHierarchy 
            hierarchy={hierarchy}
            selectedWorkItem={selectedWorkItem}
            onWorkItemSelect={onWorkItemSelect}
          />
        </AccordionDetails>
      </Accordion>
    </Box>
  );
};

export default CombinedAnalysisTab;
