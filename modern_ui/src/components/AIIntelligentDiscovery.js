import React from 'react';
import LLMPoweredRelatedWorkItems from './LLMPoweredRelatedWorkItems';

const AIIntelligentDiscovery = ({ 
  workItem, 
  semanticResults, 
  openArenaResults, 
  loading = false 
}) => {
  // Debug: Log the props being received
  console.log('🧠 AIIntelligentDiscovery props:', {
    workItem: !!workItem,
    semanticResults: !!semanticResults,
    openArenaResults: !!openArenaResults,
    loading,
    hasAnalysis: !!openArenaResults?.data?.analysis,
    analysisLength: openArenaResults?.data?.analysis?.length || 0
  });

  // Get work items from OpenArena results, same as regular Intelligent Discovery
  const getLLMPoweredWorkItems = () => {
    console.log('getLLMPoweredWorkItems called with openArenaResults:', openArenaResults);
    
    if (!openArenaResults) {
      // If no OpenArena results, return empty array
      console.log('No OpenArena results available');
      return [];
    }

    // Check if we have the structured data
    const { 
      highConfidenceItems = [], 
      mediumConfidenceItems = [], 
      lowConfidenceItems = [] 
    } = openArenaResults.data || {};

    // Combine all work items
    const allWorkItems = [
      ...highConfidenceItems,
      ...mediumConfidenceItems,
      ...lowConfidenceItems
    ];

    console.log('Combined work items for AI Intelligent Discovery:', {
      highConfidenceItems: highConfidenceItems.length,
      mediumConfidenceItems: mediumConfidenceItems.length,
      lowConfidenceItems: lowConfidenceItems.length,
      total: allWorkItems.length
    });

    return allWorkItems;
  };

  const llmWorkItems = getLLMPoweredWorkItems();
  
  return (
    <LLMPoweredRelatedWorkItems 
      workItems={llmWorkItems}
      selectedWorkItem={workItem}
      onWorkItemSelect={(id) => {
        // Handle work item selection if needed
        console.log('Work item selected:', id);
      }}
    />
  );
};

export default AIIntelligentDiscovery;