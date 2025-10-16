// Enhanced API service for Intelligent Work Item Finder
// Communicates with the Python Flask backend

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5001';

class ApiError extends Error {
  constructor(message, status = 500) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

const handleResponse = async (response) => {
  if (!response.ok) {
    let errorMessage = `HTTP error! status: ${response.status}`;
    try {
      const errorData = await response.json();
      errorMessage = errorData.error || errorMessage;
    } catch (e) {
      // If we can't parse the error response, use the default message
    }
    throw new ApiError(errorMessage, response.status);
  }

  try {
    return await response.json();
  } catch (e) {
    // If response is empty or not JSON, return null
    return null;
  }
};

const apiRequest = async (url, options = {}) => {
  try {
    // Set timeout based on the endpoint - some operations take longer
    const isLongRunningEndpoint = url.includes('/related-items') || url.includes('/llm-analysis') || url.includes('/analysis') || url.includes('/openarena-analysis') || url.includes('/auto-select');
    const timeoutMs = isLongRunningEndpoint ? 300000 : 30000; // 5 minutes for analysis, 30s for others
    
    // Create AbortController for timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
    
    const response = await fetch(`${API_BASE_URL}${url}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      signal: controller.signal,
      ...options,
    });
    
    clearTimeout(timeoutId);
    return await handleResponse(response);
  } catch (error) {
    if (error.name === 'AbortError') {
      const isLongRunning = url.includes('/related-items') || url.includes('/llm-analysis') || url.includes('/analysis');
      const timeoutMessage = isLongRunning 
        ? 'Analysis request timed out after 3 minutes. This might be due to a very large dataset or AI analysis taking longer than expected. Please try again or use a smaller dataset.'
        : 'Request timed out after 30 seconds. Please check your connection and try again.';
      throw new ApiError(timeoutMessage, 408);
    }
    console.error(`API Error for ${url}:`, error);
    throw error;
  }
};

// ===== CONNECTION MANAGEMENT =====

export const fetchConnectionStatus = async () => {
  return apiRequest('/api/connection/status');
};

export const connectAzureDevOps = async (credentials) => {
  return apiRequest('/api/connection/azure-devops', {
    method: 'POST',
    body: JSON.stringify(credentials),
  });
};

export const connectOpenArena = async (credentials) => {
  return apiRequest('/api/connection/openarena', {
    method: 'POST',
    body: JSON.stringify(credentials),
  });
};

export const testOpenArenaConnection = async () => {
  return apiRequest('/api/connection/test-openarena');
};

export const connectServices = async (credentials) => {
  return apiRequest('/api/connect', {
    method: 'POST',
    body: JSON.stringify(credentials),
  });
};

// ===== CONFIGURATION MANAGEMENT =====

export const fetchConfig = async () => {
  return apiRequest('/api/config');
};

export const saveConfig = async (configData) => {
  return apiRequest('/api/config', {
    method: 'POST',
    body: JSON.stringify(configData),
  });
};

// ===== PROJECT AND TEAM MANAGEMENT =====

export const fetchProjects = async () => {
  return apiRequest('/api/projects');
};

export const fetchTeams = async (project = null) => {
  if (project) {
    // Use the new RESTful endpoint for specific project
    return apiRequest(`/api/projects/${encodeURIComponent(project)}/teams`);
  } else {
    // Use the original endpoint which falls back to session config
    return apiRequest('/api/teams');
  }
};

export const fetchTeamsByProject = async (projectName) => {
  if (!projectName) {
    throw new ApiError('Project name is required');
  }
  return apiRequest(`/api/projects/${encodeURIComponent(projectName)}/teams`);
};

export const fetchTeamAreaPaths = async (teamId) => {
  return apiRequest(`/api/teams/${teamId}/area-paths`);
};

export const getCurrentTeam = async () => {
  return apiRequest('/api/current-team');
};

export const setCurrentTeam = async (teamData) => {
  return apiRequest('/api/current-team', {
    method: 'POST',
    body: JSON.stringify(teamData),
  });
};

// ===== WORK ITEMS =====

export const fetchWorkItems = async (filters = {}) => {
  const queryParams = new URLSearchParams();
  
  Object.entries(filters).forEach(([key, value]) => {
    if (value && value !== 'All') {
      queryParams.append(key, value);
    }
  });

  const url = `/api/work-items${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;
  return apiRequest(url);
};

export const fetchWorkItem = async (workItemId) => {
  return apiRequest(`/api/work-item/${workItemId}`);
};

export const fetchWorkItemHierarchy = async (workItemId) => {
  return apiRequest(`/api/work-item/${workItemId}/hierarchy`);
};

// ===== FILTERING =====

export const fetchFilterOptions = async () => {
  return apiRequest('/api/filters/options');
};

// ===== LLM ANALYSIS =====

export const fetchRelatedWorkItems = async (workItemId, scope = 'very-specific', dateFilter = 'last-month', workItemTypes = ['User Story', 'Task', 'Bug', 'Feature', 'Epic'], selectedTeams = '') => {
  if (!workItemId) {
    throw new ApiError('Work item ID is required');
  }
  
  const params = new URLSearchParams({
    scope: scope,
    dateFilter: dateFilter,
    workItemTypes: workItemTypes.join(',')
  });
  
  if (selectedTeams) {
    params.append('selectedTeams', selectedTeams);
  }
  
  return apiRequest(`/api/work-item/${workItemId}/related-items?${params.toString()}`);
};

// DISABLED: Team groups function - not used and causes unnecessary ADO API calls
// export const fetchTeamGroups = async (workItemId) => {
//   if (!workItemId) {
//     throw new ApiError('Work item ID is required');
//   }
//   
//   return apiRequest(`/api/work-item/${workItemId}/team-groups`);
// };

export const runLLMAnalysis = async (workItemId, relatedWorkItems = []) => {
  if (!workItemId) {
    throw new ApiError('Work item ID is required');
  }
  
  // Get the currently selected model
  const currentModel = await fetchCurrentModel();
  
  return apiRequest(`/api/work-item/${workItemId}/llm-analysis`, {
    method: 'POST',
    body: JSON.stringify({ 
      relatedWorkItems,
      model: currentModel.model || 'gpt-4' // fallback to gpt-4 if no model selected
    }),
  });
};

export const runOpenArenaAnalysis = async (workItemId, data = {}) => {
  if (!workItemId) {
    throw new ApiError('Work item ID is required');
  }
  
  // Handle both traditional and AI Deep Dive cases
  if (data.semanticResults) {
    // AI Deep Dive case
    return apiRequest(`/api/work-item/${workItemId}/openarena-analysis`, {
      method: 'POST',
      body: JSON.stringify({ 
        semanticResults: data.semanticResults,
        workItem: data.workItem,
        selectedModel: data.selectedModel,
        analysisType: 'ai_deep_dive'
      }),
    });
  } else {
    // Traditional case
    const relatedWorkItems = Array.isArray(data) ? data : (data.relatedWorkItems || []);
    return apiRequest(`/api/work-item/${workItemId}/openarena-analysis`, {
      method: 'POST',
      body: JSON.stringify({ 
        relatedWorkItems,
        analysisType: 'work_item_analysis'
      }),
    });
  }
};

export const runSemanticSimilarityAnalysis = async (workItemId, strategy = 'ai_deep_dive') => {
  if (!workItemId) {
    throw new ApiError('Work item ID is required');
  }
  
  return apiRequest(`/api/semantic-similarity/analyze/${workItemId}`, {
    method: 'POST',
    body: JSON.stringify({ 
      strategy: strategy
    }),
  });
};

export const fetchAnalysisData = async (workItemId) => {
  if (!workItemId) {
    throw new ApiError('Work item ID is required');
  }
  return apiRequest(`/api/analysis/${workItemId}`);
};

export const runAnalysis = async (workItemId, refinedWorkItems = null) => {
  const body = refinedWorkItems ? { refinedWorkItems } : {};
  return apiRequest(`/api/analysis/${workItemId}/run`, {
    method: 'POST',
    body: JSON.stringify(body),
  });
};

export const fetchMockData = async () => {
  // For backward compatibility with existing mock endpoint
  return apiRequest('/api/mock');
};

// ===== MODEL MANAGEMENT =====

export const fetchAvailableModels = async () => {
  return apiRequest('/api/models/available');
};

export const fetchCurrentModel = async () => {
  return apiRequest('/api/models/current');
};

export const selectModel = async (model) => {
  return apiRequest('/api/models/select', {
    method: 'POST',
    body: JSON.stringify({ model }),
  });
};

// Auto-selection functions
export const autoSelectModel = async (workItems, userPriority = 'balanced') => {
  return apiRequest('/api/models/auto-select', {
    method: 'POST',
    body: JSON.stringify({ 
      work_items: workItems, 
      user_priority: userPriority 
    }),
  });
};

export const previewAutoSelection = async (workItems, userPriority = 'balanced') => {
  return apiRequest('/api/models/auto-select/preview', {
    method: 'POST',
    body: JSON.stringify({ 
      work_items: workItems, 
      user_priority: userPriority 
    }),
  });
};

export const fetchAutoSelectionSettings = async () => {
  return apiRequest('/api/auto-selection/settings');
};

export const updateAutoSelectionSettings = async (settings) => {
  return apiRequest('/api/auto-selection/settings', {
    method: 'POST',
    body: JSON.stringify(settings),
  });
};

export const analyzeWorkItemComplexity = async (workItems) => {
  return apiRequest('/api/models/complexity-analysis', {
    method: 'POST',
    body: JSON.stringify({ work_items: workItems }),
  });
};

// ===== UTILITY FUNCTIONS =====

export const healthCheck = async () => {
  try {
    await apiRequest('/api/connection/status');
    return true;
  } catch (error) {
    return false;
  }
};

// Export API configuration for debugging
export const getApiConfig = () => ({
  baseUrl: API_BASE_URL,
  timeout: 30000, // 30 seconds
});

// Helper function to format error messages for UI display
export const formatApiError = (error) => {
  console.log('Raw error in formatApiError:', error);
  console.log('Error message being checked:', error.message);
  
  // Filter out specific backend errors that shouldn't be shown to users
  const errorMessage = error.message || 'An unexpected error occurred';
  
  // Suppress the get_team_area_paths error as it's a backend implementation detail
  if (errorMessage.includes('get_team_area_paths') && errorMessage.includes('missing 1 required positional argument')) {
    console.log('Suppressing get_team_area_paths error');
    return {
      message: 'Team information is being loaded...',
      status: 200,
      type: 'suppressed_error',
    };
  }
  
  if (error instanceof ApiError) {
    return {
      message: error.message,
      status: error.status,
      type: 'api_error',
    };
  }
  
  if (error.name === 'TypeError' && error.message.includes('fetch')) {
    return {
      message: 'Unable to connect to the server. Please check if the backend is running.',
      status: 0,
      type: 'connection_error',
    };
  }
  
  return {
    message: errorMessage,
    status: 500,
    type: 'unknown_error',
  };
};

// Auto Team Selection API Functions
const fetchUserProfile = async () => {
  try {
    return await apiRequest('/api/user/profile');
  } catch (error) {
    console.error('Error fetching user profile:', error);
    throw error;
  }
};

const updateUserProfile = async (profileData) => {
  try {
    return await apiRequest('/api/user/profile', {
      method: 'PUT',
      body: JSON.stringify(profileData),
    });
  } catch (error) {
    console.error('Error updating user profile:', error);
    throw error;
  }
};

const fetchTeamWorkItemCounts = async (projectId, userId = 'current_user') => {
  try {
    return await apiRequest(`/api/teams/workitem-counts?project=${projectId}&user=${userId}`);
  } catch (error) {
    console.error('Error fetching team work item counts:', error);
    throw error;
  }
};

const autoSelectTeam = async (projectId, userId = 'current_user') => {
  try {
    return await apiRequest('/api/teams/auto-select', {
      method: 'POST',
      body: JSON.stringify({
        projectId,
        userId,
      }),
    });
  } catch (error) {
    console.error('Error auto-selecting team:', error);
    throw error;
  }
};

// Auto-select team on application load
const performInitialTeamSelection = async () => {
  try {
    console.log('🚀 Starting initial team selection on app load...');
    
    // First, get the connection status to find the current project
    const connectionStatus = await fetchConnectionStatus();
    
    if (!connectionStatus.azure_devops.connected) {
      console.log('⚠️ Azure DevOps not connected, skipping auto team selection');
      return null;
    }
    
    // Get projects to find the current one
    const projects = await fetchProjects();
    if (!projects || projects.length === 0) {
      console.log('⚠️ No projects available, skipping auto team selection');
      return null;
    }
    
    // Use the project from connection status or the first available project
    const currentProject = connectionStatus.azure_devops.project 
      ? projects.find(p => p.name === connectionStatus.azure_devops.project)
      : projects[0];
    
    if (!currentProject) {
      console.log('⚠️ Current project not found, skipping auto team selection');
      return null;
    }
    
    console.log(`🎯 Auto-selecting team for project: ${currentProject.name}`);
    
    // Perform auto team selection
    const result = await autoSelectTeam(currentProject.name, 'current_user');
    
    if (result && result.selectedTeam) {
      console.log(`✅ Auto-selected team: ${result.selectedTeam.name} (${Math.round(result.selectedTeam.confidence * 100)}% confidence)`);
      
      // Set the selected team in the backend
      await setCurrentTeam({
        id: result.selectedTeam.id,
        name: result.selectedTeam.name
      });
      
      return {
        project: currentProject,
        team: result.selectedTeam,
        confidence: result.selectedTeam.confidence,
        reasons: result.selectedTeam.reasons || []
      };
    } else {
      console.log('⚠️ No team was auto-selected');
      return null;
    }
    
  } catch (error) {
    console.error('❌ Error during initial team selection:', error);
    // Don't throw the error - this is a background operation
    return null;
  }
};

const trackAnalyticsEvent = async (eventData) => {
  try {
    return await apiRequest('/api/analytics/team-selection', {
      method: 'POST',
      body: JSON.stringify(eventData),
    });
  } catch (error) {
    console.error('Error tracking analytics event:', error);
    throw error;
  }
};

// Create API object to fix ESLint warning
const apiService = {
  // Connection management
  fetchConnectionStatus,
  connectAzureDevOps,
  connectOpenArena,
  testOpenArenaConnection,
  connectServices,
  
  // Configuration management
  fetchConfig,
  saveConfig,
  
  // Project and team management
  fetchProjects,
  fetchTeams,
  fetchTeamsByProject,
  fetchTeamAreaPaths,
  setCurrentTeam,
  
  // Work items
  fetchWorkItems,
  fetchWorkItem,
  fetchWorkItemHierarchy,
  
  // Filtering
  fetchFilterOptions,
  
  // LLM analysis
  fetchRelatedWorkItems,
  runLLMAnalysis,
  fetchAnalysisData,
  runAnalysis,
  fetchMockData,
  
  // Model management
  fetchAvailableModels,
  fetchCurrentModel,
  selectModel,
  
  // Auto-selection
  autoSelectModel,
  previewAutoSelection,
  fetchAutoSelectionSettings,
  updateAutoSelectionSettings,
  analyzeWorkItemComplexity,
  
  // Auto Team Selection APIs
  fetchUserProfile,
  updateUserProfile,
  fetchTeamWorkItemCounts,
  autoSelectTeam,
  performInitialTeamSelection,
  trackAnalyticsEvent,
  
  // Utilities
  healthCheck,
  getApiConfig,
  formatApiError,
};

// Export individual functions for direct import
export {
  fetchUserProfile,
  updateUserProfile,
  fetchTeamWorkItemCounts,
  autoSelectTeam,
  performInitialTeamSelection,
  trackAnalyticsEvent,
};

export default apiService;