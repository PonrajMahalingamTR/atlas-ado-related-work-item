import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import {
  Box,
  Container,
  Paper,
  Typography,
  Button,
  Alert,
  CircularProgress,
  Tabs,
  Tab,
  Snackbar,
} from '@mui/material';
import {
  Psychology as AIIcon,
} from '@mui/icons-material';

import RelatedWorkItems from './RelatedWorkItems';
import LLMPoweredRelatedWorkItems from './LLMPoweredRelatedWorkItems';
import CombinedAnalysisTab from './CombinedAnalysisTab';
import SearchScopeFilter from './SearchScopeFilter';
import AIProgressIndicator from './AIProgressIndicator';
import SemanticAIProgressBar from './SemanticAIProgressBar';
import SemanticSimilarityAnalysis from './SemanticSimilarityAnalysis';
import AIDeepDiveWorkflow from './AIDeepDiveWorkflow';
import AIIntelligentDiscovery from './AIIntelligentDiscovery';
import AISmartAnalyticsHub from './AISmartAnalyticsHub';

import {
  fetchWorkItem,
  fetchRelatedWorkItems,
  // fetchTeamGroups, // DISABLED: Not used and causes unnecessary ADO API calls
  runOpenArenaAnalysis,
  runSemanticSimilarityAnalysis,
  fetchCurrentModel,
  fetchWorkItemHierarchy,
  formatApiError,
} from '../services/api';
import { getModelDisplayName } from './ModelIcon';
import costInfoStore from '../services/costInfoStore';
import { 
  LOADING_MESSAGES, 
  TIMING_CONFIG, 
  calculateProgress, 
  getCurrentPhase, 
  getPhaseProgress,
  createEnhancedRealTimeUpdates
} from '../config/loadingMessages';

const WorkItemAnalysis = ({ 
  connectionStatus, 
  workItemId: propWorkItemId,
  workItem: propWorkItem,
  onBackToList,
  onAnalysisDataUpdate,
  runningAnalysis: propRunningAnalysis,
  setRunningAnalysis: propSetRunningAnalysis,
  refinedWorkItems: propRefinedWorkItems,
  setRefinedWorkItems: propSetRefinedWorkItems,
  workflowStep: propWorkflowStep,
  setWorkflowStep: propSetWorkflowStep
}) => {
  const { workItemId: paramWorkItemId } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  // Helper functions for work item display (kept for future use)
  // const getStateColor = (state) => { ... }
  // const getStateIcon = (state) => { ... }
  
  // Get work item ID from props, params, or search params for backward compatibility
  const currentWorkItemId = propWorkItemId || paramWorkItemId || searchParams.get('workItemId');

  const [analysisData, setAnalysisData] = useState(null);
  const [workItem, setWorkItem] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState(0);
  const [runningAnalysis] = useState(propRunningAnalysis || false);
  const [currentModel, setCurrentModel] = useState(null);
  
  // Two-step workflow states - use props if available, otherwise local state
  const [refinedWorkItems, setRefinedWorkItems] = useState(propRefinedWorkItems || []);
  const [workflowStep, setWorkflowStep] = useState(propWorkflowStep || 'initial'); // 'initial', 'refined', 'analyzed'
  const [refiningWorkItems, setRefiningWorkItems] = useState(false);
  const [analysisProgress, setAnalysisProgress] = useState(''); // Progress message for long-running operations
  
  // Filter and search states for related work items (kept for future use)
  // const [searchTerm, setSearchTerm] = useState('');
  // const [sortBy, setSortBy] = useState('createdDate'); // 'createdDate', 'title', 'workItemType', 'assignedTo'
  // const [filterByType, setFilterByType] = useState('all'); // 'all', 'User Story', 'Task', 'Bug', etc.
  
  // Search scope filter states
  const [searchScope, setSearchScope] = useState('generic'); // 'very-specific', 'specific', 'generic'
  const [selectedTeam, setSelectedTeam] = useState('');
  const [teamGroup, setTeamGroup] = useState('');
  const [totalTeams, setTotalTeams] = useState(0);
  
  // Additional filter states
  const [dateFilter, setDateFilter] = useState('last-month');
  const [workItemTypes, setWorkItemTypes] = useState(['User Story', 'Task', 'Bug', 'Feature', 'Epic']);
  
  // Team group states
  const [groupTeams, setGroupTeams] = useState([]);
  const [selectedGroupTeams, setSelectedGroupTeams] = useState([]);
  const [allTeams, setAllTeams] = useState([]);
  const [selectedAllTeams, setSelectedAllTeams] = useState([]);
  
  // Snackbar state for notifications
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState('');
  
  // Semantic similarity analysis state
  const [semanticAnalysisData, setSemanticAnalysisData] = useState(null);
  const [semanticAnalysisError, setSemanticAnalysisError] = useState('');
  
  // OpenArena results state
  const [openArenaResults, setOpenArenaResults] = useState(null);
  const [openArenaLoading, setOpenArenaLoading] = useState(false);
  
  // AI Deep Dive workflow state
  const [aiDeepDiveResults, setAiDeepDiveResults] = useState(null);
  const [aiDeepDiveLoading, setAiDeepDiveLoading] = useState(false);
  const [aiDeepDiveError, setAiDeepDiveError] = useState('');
  
  // Hierarchy state
  const [hierarchy, setHierarchy] = useState([]);
  const [hierarchyLoading, setHierarchyLoading] = useState(false);
  
  // Raw data states for debugging/inspection
  const [rawSystemPrompt, setRawSystemPrompt] = useState(null);
  const [rawLLMResponse, setRawLLMResponse] = useState(null);
  
  // Force re-render when OpenArena results change
  const [llmPoweredKey, setLlmPoweredKey] = useState(0);
  
  // AI Progress tracking states
  const [aiProgress, setAiProgress] = useState({
    isRunning: false,
    currentStep: 0,
    totalSteps: 5,
    progress: 0,
    estimatedTime: null,
    costInfo: null,
    realTimeMessage: null
  });
  const [isStartingAnalysis, setIsStartingAnalysis] = useState(false);

  useEffect(() => {
    if (currentWorkItemId && connectionStatus.azure_devops.connected) {
      // Load current model
      loadCurrentModel();
      
      // If we have work item data passed as props, use it directly
      if (propWorkItem) {
        setWorkItem(propWorkItem);
        setLoading(false);
        
        // DISABLED: Team groups loading - not used and causes unnecessary ADO API calls
        // loadTeamGroupsOnly();
        
        // Check if we have refined work items from props
        if (propRefinedWorkItems && propRefinedWorkItems.length > 0) {
          console.log('✅ Using existing refined work items from props, skipping ADO calls');
          setRefinedWorkItems(propRefinedWorkItems);
        } else if (searchScope !== 'generic') {
          console.log('⚠️ No refined work items provided, loading from ADO...');
          loadWorkItemAndRelatedItems();
        } else {
          console.log('🚫 AI Deep Dive mode - skipping automatic loading, waiting for user action');
          // For AI Deep Dive, just load the work item without related items
          loadWorkItemOnly();
        }
      } else if (searchScope !== 'generic') {
        console.log('⚠️ No work item data provided, loading from ADO...');
        // Load work item details first, then immediately call related work items API
        loadWorkItemAndRelatedItems();
      } else {
        console.log('🚫 AI Deep Dive mode - loading work item only, no related items');
        // For AI Deep Dive, load work item and team groups but no related items
        loadWorkItemAndTeamGroupsOnly();
      }
    } else if (!currentWorkItemId) {
      setError('Work item ID is required for analysis');
      setLoading(false);
    }
  }, [currentWorkItemId, connectionStatus.azure_devops.connected, propWorkItem]);

  // Sync local refinedWorkItems state with prop changes
  useEffect(() => {
    if (propRefinedWorkItems && propRefinedWorkItems.length > 0) {
      console.log('🔄 Syncing refined work items from props:', propRefinedWorkItems.length, 'items');
      setRefinedWorkItems(propRefinedWorkItems);
    }
  }, [propRefinedWorkItems]);

  // Debug effect to track openArenaResults changes
  useEffect(() => {
    console.log('🔄 openArenaResults changed:', openArenaResults);
    if (openArenaResults) {
      console.log('🔄 OpenArena results available, confidence items:', {
        high: openArenaResults.highConfidenceItems?.length || 0,
        medium: openArenaResults.mediumConfidenceItems?.length || 0,
        low: openArenaResults.lowConfidenceItems?.length || 0
      });
      // Force re-render of LLM Powered component
      setLlmPoweredKey(prev => prev + 1);
    }
  }, [openArenaResults]);

  // Load hierarchy whenever work item changes
  useEffect(() => {
    if (workItem?.id && connectionStatus.azure_devops.connected) {
      console.log('🔍 Work item changed, loading hierarchy for:', workItem.id);
      loadWorkItemHierarchy(workItem.id);
    }
  }, [workItem?.id, connectionStatus.azure_devops.connected]);

  // Ensure activeTab is always valid for the current search scope
  useEffect(() => {
    const maxTabs = 3; // Both scopes now have 3 tabs (0-2)
    if (activeTab >= maxTabs) {
      console.log('🔄 ActiveTab out of range, resetting to 0:', { activeTab, maxTabs, searchScope });
      setActiveTab(0);
    }
  }, [searchScope, activeTab]);

  // Auto-start progress bar for AI Deep Dive when component mounts
  useEffect(() => {
    if (searchScope === 'generic' && workItem && !semanticAnalysisData && !aiProgress.isRunning && !isStartingAnalysis) {
      console.log('🚀 Auto-starting progress bar for AI Deep Dive...');
      // Add a small delay to ensure component is fully mounted
      const timeoutId = setTimeout(() => {
        handleSemanticAnalysisStart();
      }, 100);
      
      return () => clearTimeout(timeoutId);
    }
  }, [searchScope, workItem, semanticAnalysisData, aiProgress.isRunning, isStartingAnalysis]);

  const loadCurrentModel = async () => {
    try {
      const model = await fetchCurrentModel();
      setCurrentModel(model);
    } catch (err) {
      console.error('Error loading current model:', err);
    }
  };

  const loadWorkItemHierarchy = async (workItemId) => {
    console.log('🔍 loadWorkItemHierarchy called with workItemId:', workItemId);
    if (!workItemId) {
      console.log('🔍 No work item ID provided, skipping hierarchy load');
      return;
    }
    
    try {
      setHierarchyLoading(true);
      console.log('🔍 Fetching hierarchy for work item:', workItemId);
      
      const hierarchyData = await fetchWorkItemHierarchy(workItemId);
      console.log('🔍 Hierarchy data received:', hierarchyData);
      
      if (hierarchyData && Array.isArray(hierarchyData)) {
        setHierarchy(hierarchyData);
      } else {
        console.log('🔍 No hierarchy data available');
        setHierarchy([]);
      }
    } catch (error) {
      console.error('Failed to load work item hierarchy:', error);
      setHierarchy([]);
    } finally {
      setHierarchyLoading(false);
    }
  };

  // DISABLED: Team groups function - not used and causes unnecessary ADO API calls
  // const loadTeamGroupsOnly = async () => {
  //   try {
  //     console.log('⚡ Loading only team groups (no work item or related items calls)');
  //     const teamGroupsData = await fetchTeamGroups(currentWorkItemId);
  //     
  //     // Set team group data
  //     if (teamGroupsData.groupTeams) {
  //       setGroupTeams(teamGroupsData.groupTeams);
  //       // Default to all teams selected
  //       setSelectedGroupTeams(teamGroupsData.groupTeams);
  //     }
  //     
  //     // Set all teams data
  //     if (teamGroupsData.allTeams) {
  //       setAllTeams(teamGroupsData.allTeams);
  //       // Default to all teams selected for generic scope
  //       setSelectedAllTeams(teamGroupsData.allTeams);
  //     }
  //     
  //     console.log('✅ Team groups loaded successfully');
  //   } catch (err) {
  //     console.error('Error loading team groups:', err);
  //     setError('Failed to load team groups');
  //   }
  // };

  const loadWorkItemOnly = async () => {
    try {
      console.log('🔄 loadWorkItemOnly called for AI Deep Dive mode');
      setLoading(true);
      setError('');
      
      // For AI Deep Dive, we only need the work item, not team groups or hierarchy
      // This prevents unnecessary API calls that might be causing the loading issue
      const workItemResponse = await fetchWorkItem(currentWorkItemId);
      
      console.log('✅ Work item loaded successfully for AI Deep Dive');
      
      setWorkItem(workItemResponse);
      
      // Extract team information from work item
      extractTeamInfo(workItemResponse);
      
      // Set default team groups data without making API calls
      setGroupTeams([]);
      setSelectedGroupTeams([]);
      setAllTeams([]);
      setSelectedAllTeams([]);
      
      console.log('✅ loadWorkItemOnly completed - ready for AI Deep Dive');
      
    } catch (err) {
      console.error('❌ Error in loadWorkItemOnly:', err);
      const formattedError = formatApiError(err);
      setError(formattedError.message);
    } finally {
      console.log('🔄 Finally block - setting loading to false');
      setLoading(false);
    }
  };

  const loadWorkItemAndTeamGroupsOnly = async () => {
    try {
      console.log('🔄 loadWorkItemAndTeamGroupsOnly called for AI Deep Dive mode');
      setLoading(true);
      setError('');
      
      // Load work item details only (team groups disabled)
      const [workItemResponse] = await Promise.all([
        fetchWorkItem(currentWorkItemId)
        // fetchTeamGroups(currentWorkItemId) // DISABLED: Not used and causes unnecessary ADO API calls
      ]);
      
      console.log('✅ Work item loaded successfully for AI Deep Dive');
      
      setWorkItem(workItemResponse);
      
      // Extract team information from work item
      extractTeamInfo(workItemResponse);
      
      // DISABLED: Team group data loading - not used and causes unnecessary ADO API calls
      // if (teamGroupsData.groupTeams) {
      //   setGroupTeams(teamGroupsData.groupTeams);
      //   setSelectedGroupTeams(teamGroupsData.groupTeams);
      // }
      
      // if (teamGroupsData.allTeams) {
      //   setAllTeams(teamGroupsData.allTeams);
      //   setSelectedAllTeams(teamGroupsData.allTeams);
      // }
      
      console.log('✅ loadWorkItemAndTeamGroupsOnly completed - ready for AI Deep Dive');
      
    } catch (err) {
      console.error('❌ Error in loadWorkItemAndTeamGroupsOnly:', err);
      const formattedError = formatApiError(err);
      setError(formattedError.message);
    } finally {
      console.log('🔄 Finally block - setting loading to false');
      setLoading(false);
    }
  };

  const loadWorkItemAndRelatedItems = async () => {
    try {
      console.log('🔄 loadWorkItemAndRelatedItems called with searchScope:', searchScope);
      setLoading(true);
      setError('');
      
      // Load work item details only (team groups disabled)
      const [workItemResponse] = await Promise.all([
        fetchWorkItem(currentWorkItemId)
        // fetchTeamGroups(currentWorkItemId) // DISABLED: Not used and causes unnecessary ADO API calls
      ]);
      
      console.log('✅ Work item loaded successfully');
      
      setWorkItem(workItemResponse);
      
      // Extract team information from work item
      extractTeamInfo(workItemResponse);
      
      // DISABLED: Team group data loading - not used and causes unnecessary ADO API calls
      // if (teamGroupsData.groupTeams) {
      //   setGroupTeams(teamGroupsData.groupTeams);
      //   setSelectedGroupTeams(teamGroupsData.groupTeams);
      // }
      
      // if (teamGroupsData.allTeams) {
      //   setAllTeams(teamGroupsData.allTeams);
      //   setSelectedAllTeams(teamGroupsData.allTeams);
      // }
      
      // Only call related work items API for non-generic scopes
      if (searchScope !== 'generic') {
        console.log('🚀 Calling handleRefineWorkItems for scope:', searchScope);
        // Then immediately call related work items API (like tkinter GUI's "Show Related Work Items" button)
        await handleRefineWorkItems();
      } else {
        console.log('🚫 Skipping ADO search for AI Deep Dive - will use semantic similarity instead');
      }
      
      console.log('✅ loadWorkItemAndRelatedItems completed, setting loading to false');
      
    } catch (err) {
      console.error('❌ Error in loadWorkItemAndRelatedItems:', err);
      const formattedError = formatApiError(err);
      setError(formattedError.message);
    } finally {
      console.log('🔄 Finally block - setting loading to false');
      setLoading(false);
    }
  };

  const loadAnalysisData = async () => {
    try {
      setLoading(true);
      setError('');
      
      // IMPORTANT: Do NOT call fetchAnalysisData here - that triggers OpenArena calls!
      // Only load work item details. Analysis data should only be fetched when user clicks "Analysis with LLM"
      const workItemResponse = await fetchWorkItem(currentWorkItemId).catch(() => null);
      
      setWorkItem(workItemResponse);
      setAnalysisData(null); // Clear any existing analysis data
      
      if (!workItemResponse) {
        setError('Work item not found');
      }
      
    } catch (err) {
      const formattedError = formatApiError(err);
      setError(formattedError.message);
    } finally {
      setLoading(false);
    }
  };

  const extractTeamInfo = (workItem) => {
    if (!workItem) return;
    
    // Extract team information from work item area path
    const areaPath = workItem.areaPath || workItem.fields?.areaPath || '';
    
    if (areaPath) {
      // Parse area path to extract team information
      // Format is typically: "Project\Team" or "Project\Group\Team"
      const pathParts = areaPath.split('\\');
      
      if (pathParts.length >= 2) {
        // Last part is usually the team name
        const teamName = pathParts[pathParts.length - 1];
        setSelectedTeam(teamName);
        
        // Second to last part might be the group (e.g., "Accessibility")
        if (pathParts.length >= 3) {
          const groupName = pathParts[pathParts.length - 2];
          setTeamGroup(groupName);
        } else {
          // If no group, use the team name as group
          setTeamGroup(teamName);
        }
      }
    }
    
    // Set default total teams (this could be fetched from API in the future)
    setTotalTeams(349); // Based on the test results we saw earlier
  };

  const handleSearchScopeChange = (newScope) => {
    console.log('🔄 handleSearchScopeChange called with new scope:', newScope);
    setSearchScope(newScope);
    
    // Reset activeTab to 0 when switching scopes to ensure valid tab index
    setActiveTab(0);
    
    // Only trigger search immediately for Laser Focus and Balanced Search
    // AI Deep Dive should wait for user to click "Unleash AI Intelligence"
    if (currentWorkItemId && newScope !== 'generic') {
      console.log('🚀 Triggering search from handleSearchScopeChange with scope:', newScope);
      handleReRunSearch(newScope);
    } else if (newScope === 'generic') {
      console.log('🧠 AI Deep Dive selected - waiting for user to click "Unleash AI Intelligence"');
    }
  };

  const handleDateFilterChange = (newDateFilter) => {
    setDateFilter(newDateFilter);
  };

  const handleWorkItemTypesChange = (newWorkItemTypes) => {
    setWorkItemTypes(newWorkItemTypes);
  };

  const handleGroupTeamsChange = (newSelectedTeams) => {
    setSelectedGroupTeams(newSelectedTeams);
  };

  const handleAllTeamsChange = (newSelectedTeams) => {
    setSelectedAllTeams(newSelectedTeams);
  };

  // Search and filter handlers (kept for future use)
  // const handleSearchTermChange = (event) => { ... }
  // const handleSortByChange = (event) => { ... }
  // const handleFilterByTypeChange = (event) => { ... }
  // const clearFilters = () => { ... }

  // Filter and sort related work items (kept for future use)
  // const getFilteredAndSortedWorkItems = () => { ... }

  const handleReRunSearch = async (overrideScope = null) => {
    const scopeToUse = overrideScope || searchScope;
    console.log('🔄 handleReRunSearch called with workItemId:', currentWorkItemId, 'scope:', scopeToUse);
    if (!currentWorkItemId) {
      console.warn('⚠️ No work item ID, skipping search');
      return;
    }
    
    // Only make ADO calls for Laser Focus and Balanced Search, not for AI Deep Dive
    if (scopeToUse === 'generic') {
      console.log('🚫 Skipping ADO search for AI Deep Dive - will use semantic similarity instead');
      return;
    }
    
    try {
      console.log('🚀 Starting search with scope:', scopeToUse);
      setRefiningWorkItems(true);
      
      // Determine which teams to use based on scope
      let selectedTeams = '';
      if (scopeToUse === 'specific') {
        // Laser Focus: Use all verified teams instead of just selected teams
        // Filter allTeams to get only verified teams
        const verifiedTeams = allTeams.filter(team => team.verified === true);
        selectedTeams = verifiedTeams.map(team => team.name).join(',');
        console.log(`🎯 Laser Focus: Using ${verifiedTeams.length} verified teams out of ${allTeams.length} total teams`);
      } else if (scopeToUse === 'balanced') {
        // Balanced Search: Use selected group teams
        selectedTeams = selectedGroupTeams.map(team => typeof team === 'string' ? team : team.name).join(',');
        console.log(`⚖️ Balanced Search: Using ${selectedGroupTeams.length} selected group teams`);
      } else if (scopeToUse === 'generic') {
        selectedTeams = selectedAllTeams.map(team => typeof team === 'string' ? team : team.name).join(',');
      }
      // For 'very-specific', no team selection needed as it uses the work item's own team
      
      // Fetch related work items with the new scope and filters
      const result = await fetchRelatedWorkItems(currentWorkItemId, scopeToUse, dateFilter, workItemTypes, selectedTeams);
      
      // Handle both direct array response and wrapped response
      const relatedItems = Array.isArray(result) ? result : (result.relatedWorkItems || result);
      
      setRefinedWorkItems(relatedItems);
      setActiveTab(0); // Switch to Related Work Items tab
      
      console.log(`✅ Search completed successfully! Scope: '${scopeToUse}', Found: ${relatedItems.length} related items`);
      console.log('📋 Related items:', relatedItems);
      
    } catch (err) {
      const formattedError = formatApiError(err);
      console.error('❌ Error re-running search:', formattedError);
      setError(`Failed to re-run search: ${formattedError.message}`);
    } finally {
      setRefiningWorkItems(false);
      setAnalysisProgress('');
    }
  };

  const handleRefineWorkItems = async () => {
    if (!currentWorkItemId) return;
    
    // Only make ADO calls for Laser Focus and Balanced Search, not for AI Deep Dive
    if (searchScope === 'generic') {
      console.log('🚫 Skipping ADO search for AI Deep Dive - will use semantic similarity instead');
      return;
    }
    
    try {
      setRefiningWorkItems(true);
      setAnalysisProgress('Searching for related work items...');
      
      // Add progress updates for user feedback
      setTimeout(() => {
        if (refiningWorkItems) {
          setAnalysisProgress('Analyzing relationships with Azure DevOps...');
        }
      }, 5000);
      
      setTimeout(() => {
        if (refiningWorkItems) {
          setAnalysisProgress('Running advanced AI analysis (this may take up to 60 seconds)...');
        }
      }, 15000);
      
      // Determine which teams to use based on scope
      let selectedTeams = '';
      if (searchScope === 'specific') {
        // Laser Focus: Use all verified teams instead of just selected teams
        // Filter allTeams to get only verified teams
        const verifiedTeams = allTeams.filter(team => team.verified === true);
        selectedTeams = verifiedTeams.map(team => team.name).join(',');
        console.log(`🎯 Laser Focus: Using ${verifiedTeams.length} verified teams out of ${allTeams.length} total teams`);
      } else if (searchScope === 'balanced') {
        // Balanced Search: Use selected group teams
        selectedTeams = selectedGroupTeams.map(team => typeof team === 'string' ? team : team.name).join(',');
        console.log(`⚖️ Balanced Search: Using ${selectedGroupTeams.length} selected group teams`);
      } else if (searchScope === 'generic') {
        selectedTeams = selectedAllTeams.map(team => typeof team === 'string' ? team : team.name).join(',');
      }
      // For 'very-specific', no team selection needed as it uses the work item's own team
      
      // Fetch related work items using the new API endpoint with search scope and filters
      console.log(`🔍 Fetching related items for work item ${currentWorkItemId} with scope: ${searchScope}, date: ${dateFilter}, types: ${workItemTypes.join(',')}, teams: ${selectedTeams}...`);
      
      const result = await fetchRelatedWorkItems(currentWorkItemId, searchScope, dateFilter, workItemTypes, selectedTeams);
      
      console.log('✅ Related items result:', result);
      
      // Handle both direct array response and wrapped response
      const relatedItems = Array.isArray(result) ? result : (result.relatedWorkItems || result);
      
      setRefinedWorkItems(relatedItems);
      setWorkflowStep('refined');
      setActiveTab(0); // Switch to Related Work Items tab
      
      console.log(`📊 Found ${relatedItems.length} related items`);
      
    } catch (err) {
      const formattedError = formatApiError(err);
      console.error('❌ Error fetching related items:', formattedError);
      
      // Set a user-friendly error message
      if (formattedError.status === 408) {
        setError('Analysis timed out. This usually means the AI analysis took longer than expected. The system may still be processing your request - please try again in a moment.');
      } else if (formattedError.status === 404) {
        setError('Related items endpoint not found. Please make sure the backend server is running the latest version.');
      } else {
        setError(`Failed to fetch related items: ${formattedError.message}`);
      }
      throw err; // Let parent handle the error
    } finally {
      setRefiningWorkItems(false);
      setAnalysisProgress('');
    }
  };


  const handleTabChange = (event, newValue) => {
    console.log('🔄 Tab change - from:', activeTab, 'to:', newValue, 'searchScope:', searchScope);
    console.log('🔄 Tab change - event:', event);
    console.log('🔄 Tab change - newValue type:', typeof newValue);
    setActiveTab(newValue);
  };

  // Get the appropriate tabs based on search scope
  const getTabs = () => {
    // Check if we're in a loading state that should hide counts
    const isLoading = loading || refiningWorkItems || openArenaLoading || aiDeepDiveLoading;
    
    if (searchScope === 'generic') {
      // AI Deep Dive tabs
      return [
        <Tab key="0" label={`🔍 Semantic Similarity Analysis${semanticAnalysisData ? ` (${semanticAnalysisData.similar_work_items?.length || 0})` : ''}`} />,
        <Tab key="1" label="🧠 AI Intelligent Discovery" sx={{ fontWeight: 'bold', color: 'primary.main' }} />,
        <Tab key="2" label="📈 AI Smart Analytics Hub" sx={{ fontWeight: 'bold', color: 'primary.main' }} />
      ];
    } else if (searchScope === 'specific') {
      // Laser Focus - only show Azure DevOps results tab
      return [
        <Tab key="0" label={`⚙️ Fine-Tuned Azure DevOps Results${isLoading ? '' : ` (${refinedWorkItems.length})`}`} />
      ];
    } else {
      // Balanced Search tabs
      return [
        <Tab key="0" label={`⚙️ Fine-Tuned Azure DevOps Results${isLoading ? '' : ` (${refinedWorkItems.length})`}`} />,
        <Tab key="1" label={`🧠 Intelligent Discovery${isLoading ? '' : ` (${getLLMPoweredWorkItems().length})`}`} />,
        <Tab key="2" label="📈 Smart Analytics Hub" />
      ];
    }
  };

  // AI Deep Dive workflow handler
  const handleAIDeepDiveAnalysis = async () => {
    if (!currentWorkItemId || !workItem) {
      setError('Work item data is required for AI Deep Dive analysis');
      return;
    }

    try {
      setAiDeepDiveLoading(true);
      setAiDeepDiveError('');
      setError('');
      
      // Initialize AI Progress for AI Deep Dive
      setAiProgress({
        isRunning: true,
        currentStep: 1,
        totalSteps: 3,
        progress: 0,
        estimatedTime: '2-3 minutes',
        costInfo: null,
        realTimeMessage: 'Starting AI Deep Dive analysis...'
      });

      // Start real-time updates
      const interval = startSemanticRealTimeUpdates(1);
      
      // Step 1: Run semantic similarity analysis
      const semanticResult = await runSemanticSimilarityAnalysis(currentWorkItemId, 'ai_deep_dive');
      
      if (!semanticResult.success) {
        throw new Error(semanticResult.error || 'Semantic similarity analysis failed');
      }

      // Extract cost information from semantic analysis
      let semanticCostInfo = null;
      if (semanticResult && semanticResult.data && semanticResult.data.costInfo) {
        semanticCostInfo = semanticResult.data.costInfo;
      } else if (semanticResult && semanticResult.data && semanticResult.data.costTracker) {
        semanticCostInfo = {
          cost: semanticResult.data.costTracker.cost || semanticResult.data.costTracker.total_cost || 0.01,
          tokens: semanticResult.data.costTracker.tokens || 0,
          model: semanticResult.data.costTracker.model || 'semantic-similarity'
        };
      } else if (semanticResult && semanticResult.costTracker) {
        semanticCostInfo = {
          cost: semanticResult.costTracker.cost || semanticResult.costTracker.total_cost || 0.01,
          tokens: semanticResult.costTracker.tokens || 0,
          model: semanticResult.costTracker.model || 'semantic-similarity'
        };
      }
      
      // Update cost information for semantic analysis
      if (semanticCostInfo) {
        costInfoStore.setCostInfo(semanticCostInfo);
      }

      clearInterval(interval);
      
      // Step 2: Run OpenArena analysis with semantic results
      setAiProgress({
        isRunning: true,
        currentStep: 2,
        totalSteps: 3,
        progress: 50,
        estimatedTime: '1-2 minutes',
        costInfo: semanticCostInfo?.cost,
        realTimeMessage: 'Running AI analysis with semantic results...'
      });

      const openArenaResult = await runOpenArenaAnalysis(currentWorkItemId, {
        workItem: workItem,
        semanticResults: semanticResult,
        selectedModel: currentModel?.id || 'gemini2pro'
      });

      if (!openArenaResult.success) {
        throw new Error(openArenaResult.error || 'OpenArena analysis failed');
      }

      // Extract cost information from OpenArena analysis
      let openArenaCostInfo = null;
      if (openArenaResult && openArenaResult.data && openArenaResult.data.costInfo) {
        openArenaCostInfo = openArenaResult.data.costInfo;
      } else if (openArenaResult && openArenaResult.data && openArenaResult.data.costTracker) {
        openArenaCostInfo = {
          cost: openArenaResult.data.costTracker.cost || openArenaResult.data.costTracker.total_cost || 0.05,
          tokens: openArenaResult.data.costTracker.tokens || 0,
          model: openArenaResult.data.costTracker.model || currentModel?.model || 'unknown'
        };
      } else if (openArenaResult && openArenaResult.costTracker) {
        openArenaCostInfo = {
          cost: openArenaResult.costTracker.cost || openArenaResult.costTracker.total_cost || 0.05,
          tokens: openArenaResult.costTracker.tokens || 0,
          model: openArenaResult.costTracker.model || currentModel?.model || 'unknown'
        };
      }
      
      // Update cost information for OpenArena analysis
      if (openArenaCostInfo) {
        costInfoStore.setCostInfo(openArenaCostInfo);
      }

      // Step 3: Complete analysis
      setAiProgress({
        isRunning: true,
        currentStep: 3,
        totalSteps: 3,
        progress: 100,
        estimatedTime: 'Complete',
        costInfo: openArenaCostInfo?.cost,
        realTimeMessage: 'AI Deep Dive analysis complete!'
      });

      // Store results
      setAiDeepDiveResults({
        semanticResults: semanticResult,
        openArenaResults: openArenaResult,
        workflowType: 'ai_deep_dive'
      });

      // Only set OpenArena results for AI tabs (not semantic data)
      setOpenArenaResults(openArenaResult);
      setWorkflowStep('analyzed');
      setActiveTab(1); // Switch to AI Intelligent Discovery tab (tab index 1 for AI Deep Dive)
      
      // Debug: Log the results being set
      console.log('🧠 AI Deep Dive results set:', {
        semanticResult: semanticResult,
        openArenaResult: openArenaResult,
        hasAnalysis: !!openArenaResult?.data?.analysis,
        analysisLength: openArenaResult?.data?.analysis?.length || 0
      });
      
      // Show success message
      setSnackbarMessage('AI Deep Dive analysis completed successfully!');
      setSnackbarOpen(true);
      
      console.log('✅ AI Deep Dive analysis completed successfully!');
      
    } catch (err) {
      console.error('❌ AI Deep Dive analysis failed:', err);
      setAiDeepDiveError(`AI Deep Dive analysis failed: ${err.message}`);
      setError(`AI Deep Dive analysis failed: ${err.message}`);
    } finally {
      setAiDeepDiveLoading(false);
      setAiProgress({
        isRunning: false,
        currentStep: 0,
        totalSteps: 3,
        progress: 0,
        estimatedTime: null,
        costInfo: null,
        realTimeMessage: null
      });
    }
  };

  // Separate function for semantic similarity analysis (AI Deep Dive only)
  const handleSemanticSimilarityAnalysis = async () => {
    if (!currentWorkItemId || !workItem) {
      setError('Work item data is required for semantic similarity analysis');
      return;
    }

    let enhancedUpdates = null;

    try {
      setOpenArenaLoading(true);
      setError('');
      
      // Initialize AI Progress for semantic similarity
      setAiProgress({
        isRunning: true,
        currentStep: 0,
        totalSteps: 5,
        progress: 0,
        estimatedTime: '1-2 minutes',
        costInfo: null
      });

      // Start the enhanced real-time updates with phase-based timing
      enhancedUpdates = startSemanticRealTimeUpdates(1);
      
      // Wait for phases 1-4 to complete (2 minutes total)
      // During this time, the messages will show automatically with correct timing
      await new Promise(resolve => setTimeout(resolve, 120000)); // 2 minutes total
      
      // Now make the actual API call during phase 5
      console.log('🚀 Starting actual API call for semantic similarity analysis...');
      const result = await runSemanticSimilarityAnalysis(currentWorkItemId, 'ai_deep_dive');
      
      console.log('Semantic Similarity Analysis Result:', result);
      
      // Trigger phase 5 completion to show the final messages quickly
      if (enhancedUpdates && enhancedUpdates.triggerPhase5Completion) {
        enhancedUpdates.triggerPhase5Completion();
      }
      
      // Clear real-time updates
      setAiProgress(prev => ({ ...prev, realTimeMessage: null }));
      
      // Set the results - the confidence items should be in result.data
      console.log('🔍 Setting Semantic Similarity results:', result);
      console.log('🔍 Result.data:', result.data);
      
      // Process and structure the Semantic Similarity results
      const processedResults = result;
      
      // Extract similar work items from semantic similarity response
      const similarWorkItems = processedResults.similar_work_items || [];
      
      // Categorize by confidence scores
      const highConfidenceItems = similarWorkItems.filter(item => item.semanticSimilarityScore >= 0.8);
      const mediumConfidenceItems = similarWorkItems.filter(item => item.semanticSimilarityScore >= 0.6 && item.semanticSimilarityScore < 0.8);
      const lowConfidenceItems = similarWorkItems.filter(item => item.semanticSimilarityScore < 0.6);
      
      const confidenceBreakdown = {
        high: highConfidenceItems.length,
        medium: mediumConfidenceItems.length,
        low: lowConfidenceItems.length
      };
      
      // Create work items array for confidence analysis with confidence scores
      const allWorkItems = similarWorkItems.map(item => ({ 
        ...item, 
        confidence: item.semanticSimilarityScore, 
        confidenceScore: item.semanticSimilarityScore 
      }));
      
      // Extract analysis insights from the Semantic Similarity response
      const relationshipInsights = processedResults.relationship_insights || {};
      
      // Set the OpenArena results with semantic similarity data
      setOpenArenaResults({
        allWorkItems: allWorkItems,
        confidenceBreakdown: confidenceBreakdown,
        confidenceScoreChart: {
          high: highConfidenceItems.length,
          medium: mediumConfidenceItems.length,
          low: lowConfidenceItems.length
        },
        analysisInsights: {
          relationshipInsights: relationshipInsights,
          analysisType: 'semantic_similarity',
          totalFound: similarWorkItems.length
        }
      });
      
      // Set the refined work items for display
      setRefinedWorkItems(allWorkItems);
      setWorkflowStep('analyzed');
      setActiveTab(0); // Switch to Related Work Items tab
      
      console.log('✅ Semantic Similarity analysis completed successfully!');
      console.log('📊 Confidence breakdown:', confidenceBreakdown);
      console.log('📋 All work items:', allWorkItems);
      
    } catch (err) {
      const formattedError = formatApiError(err);
      console.error('❌ Error in semantic similarity analysis:', formattedError);
      setError(`Semantic similarity analysis failed: ${formattedError.message}`);
      
      // Stop enhanced updates on error
      if (enhancedUpdates && enhancedUpdates.stop) {
        enhancedUpdates.stop();
      }
    } finally {
      setOpenArenaLoading(false);
      setAiProgress(prev => ({ ...prev, isRunning: false }));
      
      // Ensure enhanced updates are stopped
      if (enhancedUpdates && enhancedUpdates.stop) {
        enhancedUpdates.stop();
      }
    }
  };

  // Semantic similarity analysis handlers
  const handleSemanticAnalysisStart = () => {
    // Prevent multiple simultaneous starts
    if (isStartingAnalysis || aiProgress.isRunning) {
      console.log('⚠️ Analysis already starting or running, skipping...');
      return;
    }
    
    console.log('🚀 handleSemanticAnalysisStart called - setting up progress tracking...');
    console.log('🔍 Current searchScope:', searchScope);
    
    setIsStartingAnalysis(true);
    
    // Stop any existing updates first
    if (window.currentSemanticUpdates && window.currentSemanticUpdates.stop) {
      console.log('🛑 Stopping existing semantic updates...');
      window.currentSemanticUpdates.stop();
    }
    
    // Initialize AI Progress for semantic similarity
    const newAiProgress = {
      isRunning: true,
      currentStep: 1,
      totalSteps: 5,
      progress: 0,
      estimatedTime: '1-2 minutes',
      costInfo: null,
      realTimeMessage: 'Initializing semantic similarity analysis...',
      currentPhase: 1,
      phaseProgress: 0
    };
    
    console.log('🎯 Setting aiProgress to:', newAiProgress);
    setAiProgress(newAiProgress);

    // Start the enhanced real-time updates with phase-based timing
    const enhancedUpdates = startSemanticRealTimeUpdates(1);
    
    // Store the enhanced updates reference for cleanup
    if (enhancedUpdates) {
      window.currentSemanticUpdates = enhancedUpdates;
    }
    
    // Reset the starting flag after a short delay
    setTimeout(() => {
      setIsStartingAnalysis(false);
    }, 1000);
  };

  const handleSemanticAnalysisComplete = (data) => {
    console.log('Semantic analysis completed:', data);
    setSemanticAnalysisData(data);
    setSemanticAnalysisError('');
    
    // Trigger phase 5 completion and stop progress
    if (window.currentSemanticUpdates && window.currentSemanticUpdates.triggerPhase5Completion) {
      window.currentSemanticUpdates.triggerPhase5Completion();
      
      // Stop updates after completion messages
      setTimeout(() => {
        setAiProgress(prev => ({ ...prev, isRunning: false, realTimeMessage: null }));
        if (window.currentSemanticUpdates && window.currentSemanticUpdates.stop) {
          window.currentSemanticUpdates.stop();
          window.currentSemanticUpdates = null;
        }
      }, 2000);
    }
  };

  const handleSemanticAnalysisError = (error) => {
    console.error('Semantic analysis error:', error);
    setSemanticAnalysisError(error);
    
    // Stop progress on error
    setAiProgress(prev => ({ ...prev, isRunning: false, realTimeMessage: null }));
    if (window.currentSemanticUpdates && window.currentSemanticUpdates.stop) {
      window.currentSemanticUpdates.stop();
      window.currentSemanticUpdates = null;
    }
  };

  // Navigation handler (kept for future use)
  // const handleBack = () => { ... }

  // Real-time AI messages for OpenArena analysis (Balanced Search)
  const aiMessages = {
    step1: [
      "🔍 Initializing work item analysis environment...",
      "📋 Loading work item data and metadata...",
      "⚙️ Preparing analysis framework...",
      "🛡️ Validating work item permissions...",
      "📊 Setting up data processing pipeline..."
    ],
    step2: [
      "📊 Processing work item hierarchies...",
      "🔗 Analyzing work item relationships...",
      "📈 Calculating initial confidence metrics...",
      "🎯 Identifying key work item attributes...",
      "⚡ Optimizing data for AI analysis..."
    ],
    step3: [
      "🧠 Activating Claude-4-Opus AI model...",
      "🔬 Initializing deep learning algorithms...",
      "⚡ Neural networks coming online...",
      "🎨 AI creativity engine starting up...",
      "🔍 Machine learning models loading..."
    ],
    step4: [
      "🌐 Connecting to OpenArena cloud infrastructure...",
      "🔗 Establishing secure connection to AI models...",
      "📝 Creating intelligent system prompt for work item analysis...",
      "🔧 Configuring AI model parameters for ADO context...",
      "📋 Analyzing work item metadata and relationships...",
      "🎯 Crafting specialized prompts for work item intelligence...",
      "⚙️ Optimizing system prompt for maximum accuracy...",
      "🛠️ Executing tool calls for work item analysis...",
      "📡 Sending structured queries to AI model...",
      "🔄 Processing API responses and data streams...",
      "⚙️ Coordinating multiple AI tool interactions...",
      "🔧 Optimizing tool call sequences for efficiency...",
      "📥 Receiving LLM response from AI model...",
      "🔍 Parsing and validating AI analysis results...",
      "📊 Extracting confidence metrics from response...",
      "🎯 Processing work item relationship data...",
      "⚡ Transforming raw AI output into structured insights...",
      "☁️ Processing results in the cloud infrastructure...",
      "🔄 Optimizing AI model performance...",
      "📈 Generating confidence metrics and analytics..."
    ],
    step5: [
      "💡 AI discovering unexpected work item correlations...",
      "🚀 Generating intelligent recommendations...",
      "🎨 Crafting unique solutions for work item challenges...",
      "🌟 Extracting actionable insights from analysis...",
      "📈 Building comprehensive work item intelligence...",
      "🔬 Advanced algorithms analyzing code patterns...",
      "🧮 Computing relationship strength metrics...",
      "🎪 Orchestrating multi-model AI analysis...",
      "⚙️ Fine-tuning analysis parameters in real-time...",
      "🚀 Deploying advanced AI reasoning capabilities...",
      "⚡ Finalizing cloud-based analysis results...",
      "🎯 Completing intelligent work item analysis..."
    ]
  };

  // Real-time updates for semantic similarity analysis (AI Deep Dive)
  const startSemanticRealTimeUpdates = (stepNumber) => {
    const updateCallback = (updateData) => {
      setAiProgress(prev => ({
        ...prev,
        realTimeMessage: updateData.message,
        progress: updateData.progress,
        currentPhase: updateData.currentPhase,
        phaseProgress: updateData.phaseProgress
      }));
    };

    const onComplete = () => {
      // Analysis complete, nothing additional needed here
    };

    const enhancedUpdates = createEnhancedRealTimeUpdates(updateCallback, onComplete);
    
    // Store the enhancedUpdates object so we can trigger phase 5 completion later
    enhancedUpdates.start();
    
    return enhancedUpdates;
  };

  const startRealTimeUpdates = (stepNumber) => {
    let messageIndex = 0;
    const stepKey = `step${stepNumber}`;
    const messages = aiMessages[stepKey] || [];
    
    const interval = setInterval(() => {
      setAiProgress(prev => ({
        ...prev,
        realTimeMessage: messages[messageIndex % messages.length]
      }));
      messageIndex++;
    }, 1200); // Change message every 1.2 seconds for more engagement

    return interval;
  };

  const handleOpenArenaAnalysis = async () => {
    if (!currentWorkItemId || !workItem) {
      setError('Work item data is required for OpenArena analysis');
      return;
    }

    try {
      setOpenArenaLoading(true);
      setError('');
      
      // Initialize AI Progress
      setAiProgress({
        isRunning: true,
        currentStep: 0,
        totalSteps: 5,
        progress: 0,
        estimatedTime: '1-2 minutes',
        costInfo: null
      });

      // Step 1: Initializing Analysis
      setAiProgress(prev => ({ ...prev, currentStep: 1, progress: 20 }));
      const step1Interval = startRealTimeUpdates(1);
      await new Promise(resolve => setTimeout(resolve, 4000)); // 4 seconds
      clearInterval(step1Interval);

      // Step 2: Data Processing
      setAiProgress(prev => ({ ...prev, currentStep: 2, progress: 40 }));
      const step2Interval = startRealTimeUpdates(2);
      await new Promise(resolve => setTimeout(resolve, 5000)); // 5 seconds
      clearInterval(step2Interval);

      // Step 3: AI Model Activation
      setAiProgress(prev => ({ ...prev, currentStep: 3, progress: 60 }));
      const step3Interval = startRealTimeUpdates(3);
      await new Promise(resolve => setTimeout(resolve, 6000)); // 6 seconds
      clearInterval(step3Interval);

      // Step 4: Cloud Analysis (actual API call)
      setAiProgress(prev => ({ ...prev, currentStep: 4, progress: 80 }));
      const step4Interval = startRealTimeUpdates(4);
      
      // Add progress updates during API call
      const progressInterval = setInterval(() => {
        setAiProgress(prev => {
          const newProgress = Math.min(prev.progress + 1, 95); // Slowly increase to 95%
          return { ...prev, progress: newProgress };
        });
      }, 1000); // Update every second
      
      // Call the OpenArena analysis API (original balanced search functionality)
      const result = await runOpenArenaAnalysis(currentWorkItemId, refinedWorkItems);
      
      // Clear progress updates
      clearInterval(progressInterval);
      clearInterval(step4Interval);
      
      console.log('OpenArena Analysis Result:', result);
      
      // Step 5: Intelligence Extraction
      setAiProgress(prev => ({ ...prev, currentStep: 5, progress: 100 }));
      const step5Interval = startRealTimeUpdates(5);
      await new Promise(resolve => setTimeout(resolve, 3000)); // 3 seconds
      clearInterval(step5Interval);
      
      // Clear real-time updates
      setAiProgress(prev => ({ ...prev, realTimeMessage: null }));
      
      // Set the results - the confidence items should be in result.data
      console.log('🔍 Setting OpenArena results:', result);
      console.log('🔍 Result.data:', result.data);
      
      // Process and structure the OpenArena results
      const processedResults = result.data || result;
      
      // Extract confidence breakdown from the actual OpenArena structure
      const highConfidenceItems = processedResults.highConfidenceItems || [];
      const mediumConfidenceItems = processedResults.mediumConfidenceItems || [];
      const lowConfidenceItems = processedResults.lowConfidenceItems || [];
      
      const confidenceBreakdown = {
        high: highConfidenceItems.length,
        medium: mediumConfidenceItems.length,
        low: lowConfidenceItems.length
      };
      
      // Create work items array for confidence analysis with confidence scores
      const allWorkItems = [
        ...highConfidenceItems.map(item => ({ ...item, confidence: 0.9, confidenceScore: 0.9 })),
        ...mediumConfidenceItems.map(item => ({ ...item, confidence: 0.6, confidenceScore: 0.6 })),
        ...lowConfidenceItems.map(item => ({ ...item, confidence: 0.3, confidenceScore: 0.3 }))
      ];
      
      // Extract analysis insights from the OpenArena response
      let analysisInsights = {
        riskAssessment: processedResults.riskAssessment || processedResults.risks || [],
        opportunities: processedResults.opportunities || [],
        dependencies: processedResults.dependencies || [],
        recommendations: processedResults.recommendations || []
      };
      
      // Parse the raw LLM response to extract structured insights
      const rawResponse = processedResults.analysisResults || processedResults.rawResponse || '';
      if (rawResponse && typeof rawResponse === 'string') {
        console.log('🔍 Parsing raw LLM response for insights:', rawResponse);
        
        // Parse Risk Assessment section
        const riskSection = rawResponse.match(/## RISK ASSESSMENT([\s\S]*?)(?=## |$)/i);
        if (riskSection) {
          const riskContent = riskSection[1];
          const riskItems = [];
          
          // Extract high-risk dependencies
          const highRiskMatch = riskContent.match(/- \*\*High-Risk Dependencies\*\*:([\s\S]*?)(?=- \*\*|$)/i);
          if (highRiskMatch) {
            riskItems.push({
              id: 'risk-high-deps',
              title: 'High-Risk Dependencies',
              description: highRiskMatch[1].trim(),
              severity: 'high',
              type: 'risk'
            });
          }
          
          // Extract blocking issues
          const blockingMatch = riskContent.match(/- \*\*Blocking Issues\*\*:([\s\S]*?)(?=- \*\*|$)/i);
          if (blockingMatch) {
            riskItems.push({
              id: 'risk-blocking',
              title: 'Blocking Issues',
              description: blockingMatch[1].trim(),
              severity: 'medium',
              type: 'risk'
            });
          }
          
          // Extract resource conflicts
          const resourceMatch = riskContent.match(/- \*\*Resource Conflicts\*\*:([\s\S]*?)(?=- \*\*|$)/i);
          if (resourceMatch) {
            riskItems.push({
              id: 'risk-resource',
              title: 'Resource Conflicts',
              description: resourceMatch[1].trim(),
              severity: 'medium',
              type: 'risk'
            });
          }
          
          analysisInsights.riskAssessment = riskItems;
        }
        
        // Parse Recommendations section
        const recSection = rawResponse.match(/## RECOMMENDATIONS([\s\S]*?)(?=## |$)/i);
        if (recSection) {
          const recContent = recSection[1];
          const recItems = [];
          
          // Extract immediate actions
          const immediateMatch = recContent.match(/- \*\*Immediate Actions\*\*:([\s\S]*?)(?=- \*\*|$)/i);
          if (immediateMatch) {
            const actions = immediateMatch[1].split(/\d+\./).filter(action => action.trim()).slice(0, 3);
            actions.forEach((action, index) => {
              recItems.push({
                id: `rec-immediate-${index}`,
                title: `Immediate Action ${index + 1}`,
                description: action.trim(),
                priority: 'high',
                type: 'recommendation'
              });
            });
          }
          
          // Extract planning considerations
          const planningMatch = recContent.match(/- \*\*Planning Considerations\*\*:([\s\S]*?)(?=- \*\*|$)/i);
          if (planningMatch) {
            const plans = planningMatch[1].split(/\d+\./).filter(plan => plan.trim()).slice(0, 2);
            plans.forEach((plan, index) => {
              recItems.push({
                id: `rec-planning-${index}`,
                title: `Planning Consideration ${index + 1}`,
                description: plan.trim(),
                priority: 'medium',
                type: 'recommendation'
              });
            });
          }
          
          analysisInsights.recommendations = recItems;
        }
        
        // Parse Relationship Patterns for Opportunities and Dependencies
        const patternsSection = rawResponse.match(/## RELATIONSHIP PATTERNS ANALYSIS([\s\S]*?)(?=## |$)/i);
        if (patternsSection) {
          const patternsContent = patternsSection[1];
          
          // Extract opportunities from patterns
          const oppItems = [];
          const primaryMatch = patternsContent.match(/- \*\*Primary Patterns\*\*:([\s\S]*?)(?=- \*\*|$)/i);
          if (primaryMatch) {
            const patterns = primaryMatch[1].split('- ').filter(pattern => pattern.trim()).slice(0, 2);
            patterns.forEach((pattern, index) => {
              oppItems.push({
                id: `opp-pattern-${index}`,
                title: `Pattern Analysis ${index + 1}`,
                description: pattern.trim(),
                type: 'opportunity'
              });
            });
          }
          
          analysisInsights.opportunities = oppItems;
          
          // Extract dependencies from clusters
          const depItems = [];
          const clusterMatch = patternsContent.match(/- \*\*Dependency Clusters\*\*:([\s\S]*?)(?=- \*\*|$)/i);
          if (clusterMatch) {
            const clusters = clusterMatch[1].split('- ').filter(cluster => cluster.trim()).slice(0, 2);
            clusters.forEach((cluster, index) => {
              depItems.push({
                id: `dep-cluster-${index}`,
                title: `Dependency Cluster ${index + 1}`,
                description: cluster.trim(),
                status: 'coordination',
                type: 'dependency'
              });
            });
          }
          
          analysisInsights.dependencies = depItems;
        }
      }
      
      // If still no insights are available, generate sample insights based on work items
      if (Object.values(analysisInsights).every(arr => arr.length === 0)) {
        const totalItems = allWorkItems.length;
        analysisInsights = {
          riskAssessment: [
            {
              id: 'risk-1',
              title: 'High Dependency on Technical Infrastructure',
              description: `The selected work item depends heavily on ${totalItems} related work items. Any delays in the technical foundation could impact the implementation.`,
              severity: 'medium',
              type: 'risk'
            }
          ],
          opportunities: [
            {
              id: 'opp-1',
              title: 'Consolidate Related Work Items',
              description: `Multiple work items (${totalItems}) are related to this work item. Consider coordinating these efforts to create a comprehensive solution.`,
              type: 'opportunity'
            }
          ],
          dependencies: [
            {
              id: 'dep-1',
              title: 'Related Work Items Coordination',
              description: `${totalItems} work items should be coordinated with the selected work item to ensure consistent implementation.`,
              status: 'coordination',
              type: 'dependency'
            }
          ],
          recommendations: [
            {
              id: 'rec-1',
              title: 'Prioritize Related Work Items',
              description: `Ensure ${totalItems} related work items are completed before starting the selected work item to avoid rework.`,
              priority: 'high',
              type: 'recommendation'
            }
          ]
        };
      }
      
      // Create confidence score chart data
      const confidenceScoreChart = {
        distribution: {
          high: confidenceBreakdown.high,
          medium: confidenceBreakdown.medium,
          low: confidenceBreakdown.low
        },
        byState: processedResults.confidenceByState || {}
      };
      
      // Store raw data for debugging/inspection
      if (result && result.data) {
        setRawSystemPrompt(result.data.systemPrompt || 'System prompt not available');
        setRawLLMResponse(result.data.analysisResults || result.data.rawResponse || 'Raw response not available');
      }
      
      // Set the processed results
      setOpenArenaResults({
        ...processedResults,
        analysisInsights,
        confidenceBreakdown,
        confidenceScoreChart,
        allWorkItems
      });
      
      // Extract cost information if available
      let costInfo = null;
      if (result && result.data && result.data.costInfo) {
        costInfo = result.data.costInfo;
      } else if (result && result.data && result.data.costTracker) {
        costInfo = {
          cost: result.data.costTracker.cost || result.data.costTracker.total_cost || 0.05,
          tokens: result.data.costTracker.tokens || 0,
          model: result.data.costTracker.model || currentModel?.model || 'unknown'
        };
      } else if (result && result.costTracker) {
        costInfo = {
          cost: result.costTracker.cost || result.costTracker.total_cost || 0.05,
          tokens: result.costTracker.tokens || 0,
          model: result.costTracker.model || currentModel?.model || 'unknown'
        };
      }
      
      setAiProgress(prev => ({ 
        ...prev, 
        costInfo: costInfo?.cost,
        estimatedTime: null 
      }));
      
      // Update cost information via global store (no React re-renders)
      if (costInfo) {
        costInfoStore.setCostInfo(costInfo);
      }
      
      setActiveTab(1); // Switch to Intelligent Discovery tab to show the analysis results
      
      setSnackbarMessage('OpenArena analysis completed successfully!');
      setSnackbarOpen(true);
      
    } catch (err) {
      const formattedError = formatApiError(err);
      let errorMessage = `OpenArena analysis failed: ${formattedError.message}`;
      
      // Provide more specific error messages for common issues
      if (err.name === 'AbortError') {
        errorMessage = 'OpenArena analysis timed out. The analysis is taking longer than expected. Please try again.';
      } else if (formattedError.message.includes('timeout')) {
        errorMessage = 'OpenArena analysis timed out. Please check your connection and try again.';
      } else if (formattedError.message.includes('network')) {
        errorMessage = 'Network error during OpenArena analysis. Please check your connection and try again.';
      } else if (formattedError.message.includes('Azure OpenAI API key')) {
        errorMessage = 'Azure OpenAI API key not configured. Please set up your Azure OpenAI credentials to use semantic similarity features.';
      }
      
      setError(errorMessage);
      console.error('OpenArena analysis error:', formattedError);
    } finally {
      setOpenArenaLoading(false);
      // Clear any remaining intervals and updates
      setAiProgress(prev => ({ ...prev, realTimeMessage: null }));
      // Reset progress after a delay to show completion
      setTimeout(() => {
        setAiProgress(prev => ({ ...prev, isRunning: false }));
      }, 2000);
    }
  };

  const handleLaunchModernUI = () => {
    if (openArenaResults) {
      // Navigate to the modern UI view with the OpenArena results
      navigate(`/analysis/${currentWorkItemId}?tab=openarena&results=${encodeURIComponent(JSON.stringify(openArenaResults))}`);
    }
  };

  // Function to get LLM-powered work items with proper confidence scores
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
    } = openArenaResults;

    console.log('🔍 Confidence items found:', {
      high: highConfidenceItems.length,
      medium: mediumConfidenceItems.length,
      low: lowConfidenceItems.length,
      openArenaResultsKeys: Object.keys(openArenaResults)
    });

    // Combine all confidence levels into a single array and remove duplicates
    const allLLMItems = [
      ...highConfidenceItems,
      ...mediumConfidenceItems,
      ...lowConfidenceItems
    ];

    // Remove duplicates based on work item ID
    const uniqueItems = [];
    const seenIds = new Set();
    for (const item of allLLMItems) {
      if (!seenIds.has(item.id)) {
        seenIds.add(item.id);
        uniqueItems.push(item);
      }
    }

    console.log('LLM Powered Work Items Debug:', {
      openArenaResults: openArenaResults,
      total: uniqueItems.length,
      high: highConfidenceItems.length,
      medium: mediumConfidenceItems.length,
      low: lowConfidenceItems.length,
      sampleItem: uniqueItems[0],
      allKeys: Object.keys(openArenaResults || {}),
      // Add detailed structure inspection
      openArenaResultsKeys: Object.keys(openArenaResults || {}),
      openArenaResultsValues: Object.values(openArenaResults || {}),
      hasHighConfidenceItems: 'highConfidenceItems' in (openArenaResults || {}),
      hasMediumConfidenceItems: 'mediumConfidenceItems' in (openArenaResults || {}),
      hasLowConfidenceItems: 'lowConfidenceItems' in (openArenaResults || {}),
      duplicatesRemoved: allLLMItems.length - uniqueItems.length
    });

    // If no LLM items found, return empty array
    if (uniqueItems.length === 0) {
      console.log('No LLM items found in OpenArena results, returning empty array');
      return [];
    }

    return uniqueItems;
  };

  if (!connectionStatus.azure_devops.connected) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Alert severity="warning">
          Please connect to Azure DevOps first to view work item analysis.
        </Alert>
      </Container>
    );
  }

  if (!currentWorkItemId) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Alert severity="error">
          Work item ID is required for analysis. Please select a work item from the work items list.
        </Alert>
      </Container>
    );
  }

  // Remove the early return for loading states - we'll show the UI with loading indicators instead

  if (error) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Alert severity="error" action={
          <Button color="inherit" size="small" onClick={loadAnalysisData}>
            Retry
          </Button>
        }>
          {error}
        </Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="xl" sx={{ py: 0 }}>
      <Box sx={{ mt: 0 }}>
        {/* Action Buttons Header - HIDDEN */}


      {/* Search Scope Filter - Always visible */}
      <Box sx={{ mt: 1 }}>
        <SearchScopeFilter
          searchScope={searchScope}
          onScopeChange={handleSearchScopeChange}
          selectedTeam={selectedTeam}
          teamGroup={teamGroup}
          totalTeams={totalTeams}
          onReRunSearch={handleReRunSearch}
          isSearching={refiningWorkItems}
          dateFilter={dateFilter}
          onDateFilterChange={handleDateFilterChange}
          workItemTypes={workItemTypes}
          onWorkItemTypesChange={handleWorkItemTypesChange}
          groupTeams={groupTeams}
          selectedGroupTeams={selectedGroupTeams}
          onGroupTeamsChange={handleGroupTeamsChange}
          allTeams={allTeams}
          selectedAllTeams={selectedAllTeams}
          onAllTeamsChange={handleAllTeamsChange}
          loading={loading}
          refinedWorkItems={refinedWorkItems}
          onUnleashAI={searchScope === 'generic' ? handleAIDeepDiveAnalysis : handleOpenArenaAnalysis}
          runningAnalysis={runningAnalysis}
          openArenaLoading={openArenaLoading}
        />
      </Box>

      {/* AI Progress Indicator - Shows during Balanced Search analysis */}
      <AIProgressIndicator
        isRunning={aiProgress.isRunning && searchScope !== 'generic'}
        progress={aiProgress.progress}
        currentStep={aiProgress.currentStep}
        totalSteps={aiProgress.totalSteps}
        estimatedTime={aiProgress.estimatedTime}
        costInfo={aiProgress.costInfo}
        relatedWorkItemsCount={refinedWorkItems.length}
        realTimeMessage={aiProgress.realTimeMessage}
        currentModel={getModelDisplayName(currentModel?.model)}
        iconType={7} // Hologram icon only
        cycleIcons={false} // Disable cycling - show only hologram icon
      />

      {/* Semantic AI Progress Bar - Shows during AI Deep Dive analysis */}
      {(() => {
        // Show progress bar for AI Deep Dive (generic search scope) when:
        // 1. aiProgress.isRunning is true (callback-based), OR
        // 2. We're on AI Deep Dive tab and no analysis data yet (fallback detection)
        const isAIDeepDive = searchScope === 'generic';
        const hasAnalysisData = !!semanticAnalysisData;
        const isOnAIDeepDiveTab = activeTab === 0; // Tab 0 is the first AI Deep Dive tab
        
        const shouldShowProgressBar = isAIDeepDive && (
          aiProgress.isRunning || 
          (isOnAIDeepDiveTab && !hasAnalysisData)
        );
        
        console.log('🔍 SemanticAIProgressBar render check:', {
          'aiProgress.isRunning': aiProgress.isRunning,
          'searchScope': searchScope,
          'activeTab': activeTab,
          'isAIDeepDive': isAIDeepDive,
          'hasAnalysisData': hasAnalysisData,
          'isOnAIDeepDiveTab': isOnAIDeepDiveTab,
          'shouldShowProgressBar': shouldShowProgressBar,
          'aiProgress': aiProgress
        });
        
        return (
          <SemanticAIProgressBar
            isRunning={shouldShowProgressBar}
            progress={aiProgress.progress || 0}
            currentPhase={aiProgress.currentPhase || 1}
            phaseProgress={aiProgress.phaseProgress || 0}
            realTimeMessage={aiProgress.realTimeMessage || 'Initializing semantic analysis...'}
            estimatedTime={aiProgress.estimatedTime || '1-2 minutes'}
            costInfo={aiProgress.costInfo}
            currentModel={getModelDisplayName(currentModel?.model)}
            iconType={7}
            cycleIcons={false}
          />
        );
      })()}


      {/* Tabs for Related Work Items - Always visible */}
      <Paper sx={{ mb: 1, mt: 1 }}>
        <Tabs
          key={`tabs-${searchScope}`}
          value={activeTab}
          onChange={handleTabChange}
          variant="scrollable"
          scrollButtons="auto"
          aria-label="analysis tabs"
          indicatorColor="primary"
          textColor="primary"
        >
          {getTabs()}
          {/* Debug info */}
          {console.log('🔍 Tab rendering - searchScope:', searchScope, 'activeTab:', activeTab, 'isGeneric:', searchScope === 'generic')}
        </Tabs>
      </Paper>

      {/* Tab Panels - Always visible */}
      <Box>
        {(loading || refiningWorkItems) && searchScope !== 'generic' ? (
          /* Loading state for content - only show for non-generic scopes */
          <Paper sx={{ p: 4, textAlign: 'center' }}>
            <CircularProgress size={40} sx={{ mb: 2 }} />
            <Typography variant="h6" gutterBottom>
              📡 Deep-Diving into Azure DevOps...
            </Typography>
          </Paper>
        ) : workflowStep === 'analyzed' && analysisData ? (
          /* Step 3: Analysis Complete - Show Results */
          <Box>
            {/* Analysis results content */}
            <Typography variant="h6" gutterBottom>
              Analysis Complete
            </Typography>
            <Typography variant="body2" color="text.secondary">
              AI analysis has been completed. Results are available in the tabs above.
            </Typography>
          </Box>
        ) : (
          /* Normal content display when not loading */
          <Box>
            {/* Laser Focus & Balanced Search tabs */}
            {searchScope !== 'generic' && (
              <>
                {activeTab === 0 && (
                  <Box>
                    <RelatedWorkItems 
                      workItems={refinedWorkItems}
                      selectedWorkItem={workItem}
                      onWorkItemSelect={(id) => navigate(`/analysis/${id}`)}
                    />
                  </Box>
                )}
                
                {activeTab === 1 && searchScope !== 'specific' && (() => {
                  const llmWorkItems = getLLMPoweredWorkItems();
                  console.log('🎯 Intelligent Discovery Tab - Rendering with workItems:', llmWorkItems);
                  return (
                    <LLMPoweredRelatedWorkItems 
                      key={llmPoweredKey}
                      workItems={llmWorkItems}
                      selectedWorkItem={workItem}
                      onWorkItemSelect={(id) => navigate(`/analysis/${id}`)}
                    />
                  );
                })()}
                
                {activeTab === 2 && searchScope !== 'specific' && (
                  <>
                    {console.log('Comprehensive Analysis Tab - hierarchy:', hierarchy)}
                    {console.log('Comprehensive Analysis Tab - openArenaResults:', openArenaResults)}
                    <CombinedAnalysisTab 
                      hierarchy={hierarchy}
                      hierarchyLoading={hierarchyLoading}
                      workItems={openArenaResults?.allWorkItems || getLLMPoweredWorkItems()}
                      confidenceBreakdown={openArenaResults?.confidenceBreakdown || {}}
                      chartData={openArenaResults?.confidenceScoreChart || {}}
                      insights={openArenaResults?.analysisInsights || {}}
                      selectedWorkItem={workItem}
                      onWorkItemSelect={(id) => navigate(`/analysis/${id}`)}
                    />
                  </>
                )}
              </>
            )}

            {/* AI Deep Dive tabs */}
            {searchScope === 'generic' && (
              <>
                {activeTab === 0 && (
                  <SemanticSimilarityAnalysis
                    workItemId={currentWorkItemId}
                    workItem={workItem}
                    onAnalysisStart={handleSemanticAnalysisStart}
                    onAnalysisComplete={handleSemanticAnalysisComplete}
                    onError={handleSemanticAnalysisError}
                  />
                )}
                
                {activeTab === 1 && (() => {
                  const llmWorkItems = getLLMPoweredWorkItems();
                  console.log('🧠 AI Intelligent Discovery Tab - Rendering with workItems:', llmWorkItems);
                  return (
                    <AIIntelligentDiscovery 
                      workItem={workItem}
                      semanticResults={semanticAnalysisData}
                      openArenaResults={openArenaResults}
                      loading={aiDeepDiveLoading}
                    />
                  );
                })()}

                {activeTab === 2 && (
                  <>
                    {console.log('📈 AI Smart Analytics Hub - hierarchy:', hierarchy)}
                    {console.log('📈 AI Smart Analytics Hub - openArenaResults:', openArenaResults)}
                    <AISmartAnalyticsHub 
                      workItem={workItem}
                      semanticResults={semanticAnalysisData}
                      openArenaResults={openArenaResults}
                      loading={aiDeepDiveLoading}
                    />
                  </>
                )}
              </>
            )}
            
          </Box>
        )}
      </Box>

      {/* Analysis Complete Section - Only show when analysis is done */}
      {workflowStep === 'analyzed' && analysisData && (
        <Box sx={{ mt: 2 }}>
          {/* Tabs */}
          <Paper sx={{ mb: 2 }}>
            <Tabs
              value={activeTab}
              onChange={handleTabChange}
              variant="scrollable"
              scrollButtons="auto"
            >
              <Tab label={`⚙️ Fine-Tuned Azure DevOps Results${(loading || refiningWorkItems || openArenaLoading || aiDeepDiveLoading) ? '' : ` (${refinedWorkItems.length})`}`} />
              <Tab label={`🧠 Intelligent Discovery${(loading || refiningWorkItems || openArenaLoading || aiDeepDiveLoading) ? '' : ` (${getLLMPoweredWorkItems().length})`}`} />
              <Tab label={`🔍 Semantic Similarity Analysis${semanticAnalysisData ? ` (${semanticAnalysisData.similar_work_items?.length || 0})` : ''}`} />
              <Tab label="📈 Smart Analytics Hub" />
              {/* Debug info */}
              {console.log('🔍 Tab rendering - searchScope:', searchScope, 'isGeneric:', searchScope === 'generic')}
            </Tabs>
          </Paper>

          {/* Tab Panels */}
          <Box>
            {activeTab === 0 && (
              <RelatedWorkItems 
                workItems={workflowStep === 'refined' ? refinedWorkItems : (analysisData?.relatedWorkItems || [])}
                selectedWorkItem={workItem}
                onWorkItemSelect={(id) => navigate(`/analysis/${id}`)}
              />
            )}
            
            {activeTab === 1 && (
              <LLMPoweredRelatedWorkItems 
                workItems={workflowStep === 'refined' ? refinedWorkItems : (analysisData?.relatedWorkItems || [])}
                selectedWorkItem={workItem}
                onWorkItemSelect={(id) => navigate(`/analysis/${id}`)}
              />
            )}
            
            {activeTab === 2 && searchScope === 'generic' && (
              <SemanticSimilarityAnalysis
                workItemId={currentWorkItemId}
                workItem={workItem}
                onAnalysisStart={handleSemanticAnalysisStart}
                onAnalysisComplete={handleSemanticAnalysisComplete}
                onError={handleSemanticAnalysisError}
              />
            )}
            
            {activeTab === 2 && searchScope !== 'generic' && (
              <Box sx={{ p: 3, textAlign: 'center' }}>
                <Typography variant="h6" color="text.secondary" gutterBottom>
                  Semantic Similarity Analysis
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  This analysis is only available for AI Deep Dive strategy. 
                  Please select "🧠 AI Deep Dive" to use semantic similarity analysis.
                </Typography>
              </Box>
            )}
            
            {activeTab === 3 && (
              <>
                {console.log('Analysis Complete - Comprehensive Analysis Tab - hierarchy:', hierarchy)}
                {console.log('Analysis Complete - Comprehensive Analysis Tab - analysisData:', analysisData)}
                <CombinedAnalysisTab 
                  hierarchy={hierarchy}
                  hierarchyLoading={hierarchyLoading}
                  workItems={analysisData?.relatedWorkItems || []}
                  confidenceBreakdown={analysisData?.confidenceBreakdown || {}}
                  chartData={analysisData?.confidenceScoreChart || {}}
                  insights={analysisData?.analysisInsights || {}}
                  selectedWorkItem={workItem}
                  onWorkItemSelect={(id) => navigate(`/analysis/${id}`)}
                />
              </>
            )}
          </Box>
        </Box>
      )}
      
      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbarOpen}
        autoHideDuration={3000}
        onClose={() => setSnackbarOpen(false)}
        message={snackbarMessage}
      />
      </Box>
    </Container>
  );
};

export default WorkItemAnalysis;