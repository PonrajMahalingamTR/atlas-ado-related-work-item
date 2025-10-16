import React, { useState, useEffect } from 'react';
import CombinedAnalysisTab from './CombinedAnalysisTab';
import { fetchWorkItemHierarchy } from '../services/api';

const AISmartAnalyticsHub = ({ 
  workItem, 
  semanticResults, 
  openArenaResults, 
  loading = false 
}) => {
  // State for hierarchy data
  const [hierarchy, setHierarchy] = useState([]);
  const [hierarchyLoading, setHierarchyLoading] = useState(false);

  // Debug: Log the props being received
  console.log('📈 AISmartAnalyticsHub props:', {
    workItem: !!workItem,
    semanticResults: !!semanticResults,
    openArenaResults: !!openArenaResults,
    loading,
    hasAnalysis: !!openArenaResults?.data?.analysis,
    analysisLength: openArenaResults?.data?.analysis?.length || 0
  });

  // Fetch hierarchy data when work item changes
  useEffect(() => {
    const loadHierarchy = async () => {
      if (!workItem?.id) {
        console.log('📈 No work item ID available for hierarchy');
        return;
      }

      try {
        setHierarchyLoading(true);
        console.log('📈 Fetching hierarchy for work item:', workItem.id);
        
        const hierarchyData = await fetchWorkItemHierarchy(workItem.id);
        console.log('📈 Hierarchy data received:', hierarchyData);
        
        if (hierarchyData && Array.isArray(hierarchyData)) {
          setHierarchy(hierarchyData);
        } else {
          console.log('📈 No hierarchy data available');
          setHierarchy([]);
        }
      } catch (error) {
        console.error('📈 Failed to load work item hierarchy:', error);
        setHierarchy([]);
      } finally {
        setHierarchyLoading(false);
      }
    };

    loadHierarchy();
  }, [workItem?.id]);

  // Transform OpenArena results to match regular Smart Analytics Hub structure
  const transformOpenArenaResults = () => {
    if (!openArenaResults) {
      return {
        allWorkItems: [],
        confidenceBreakdown: { high: 0, medium: 0, low: 0 },
        confidenceScoreChart: { high: 0, medium: 0, low: 0 },
        analysisInsights: {}
      };
    }

    // Extract work items from the parsed LLM response
    const highConfidenceItems = openArenaResults.data?.highConfidenceItems || [];
    const mediumConfidenceItems = openArenaResults.data?.mediumConfidenceItems || [];
    const lowConfidenceItems = openArenaResults.data?.lowConfidenceItems || [];

    // Combine all work items and convert confidence strings to numeric values
    const allWorkItems = [
      ...highConfidenceItems.map(item => ({ ...item, confidence: 0.9, confidenceScore: 0.9 })),
      ...mediumConfidenceItems.map(item => ({ ...item, confidence: 0.6, confidenceScore: 0.6 })),
      ...lowConfidenceItems.map(item => ({ ...item, confidence: 0.3, confidenceScore: 0.3 }))
    ];

    // Create confidence breakdown
    const confidenceBreakdown = {
      high: highConfidenceItems.length,
      medium: mediumConfidenceItems.length,
      low: lowConfidenceItems.length
    };

    // Create chart data (same as confidence breakdown)
    const confidenceScoreChart = {
      high: highConfidenceItems.length,
      medium: mediumConfidenceItems.length,
      low: lowConfidenceItems.length
    };

    // Create insights from the parsed analysis
    const insights = {
      relationshipInsights: {
        patterns: openArenaResults.data?.relationshipPatterns || [],
        riskAssessment: openArenaResults.data?.riskAssessment || [],
        recommendations: openArenaResults.data?.recommendations || []
      },
      analysisInsights: {
        summary: openArenaResults.data?.summary || {},
        analysisType: 'ai_deep_dive',
        totalFound: allWorkItems.length
      }
    };

    return {
      allWorkItems,
      confidenceBreakdown,
      confidenceScoreChart,
      analysisInsights: insights
    };
  };

  const transformedData = transformOpenArenaResults();
  const llmWorkItems = transformedData.allWorkItems;
  const confidenceBreakdown = transformedData.confidenceBreakdown;
  const chartData = transformedData.confidenceScoreChart;
  const insights = transformedData.analysisInsights;

  console.log('AI Smart Analytics Hub transformed data:', {
    workItems: llmWorkItems.length,
    confidenceBreakdown,
    chartData,
    insights,
    openArenaResults: !!openArenaResults,
    rawData: openArenaResults?.data
  });

  // Use the real hierarchy from ADO API call

  return (
    <CombinedAnalysisTab 
      hierarchy={hierarchy}
      hierarchyLoading={hierarchyLoading}
      workItems={llmWorkItems}
      confidenceBreakdown={confidenceBreakdown}
      chartData={chartData}
      insights={insights}
      selectedWorkItem={workItem}
      onWorkItemSelect={(id) => {
        // Handle work item selection if needed
        console.log('Work item selected:', id);
      }}
    />
  );
};

export default AISmartAnalyticsHub;