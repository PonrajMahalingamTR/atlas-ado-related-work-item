/**
 * Loading Messages Configuration for Semantic Similarity Analysis
 * 
 * This file contains updated loading messages organized across 5 phases:
 * - Phase 1: ADO Search & System Prompt Creation (4 messages)
 * - Phase 2: LLM Analysis & Response Processing (8 messages)
 * - Phase 3: Embedding Generation (4 messages)
 * - Phase 4: Vector Database (6 messages)
 * - Phase 5: Vector Similarity Search (6 messages)
 * 
 * Total Duration: 1 minute (60 seconds)
 * Message Interval: Variable per phase
 * Total Messages: 28 messages
 * 
 * Updated with more detailed, accurate progress indicators
 */

export const LOADING_MESSAGES = {
  // Phase 1: ADO Search & System Prompt Creation (4 messages)
  phase1: [
    "🤖 Initializing Azure DevOps search for work item...",
    "⚡ Successfully retrieved related work items with expanded fields",
    "🧠 Preparing system prompt for AI analysis...",
    "📝 Creating structured embedding generation prompt..."
  ],

  // Phase 2: LLM Analysis & Response Processing (8 messages)
  phase2: [
    "🚀 Sending request to OpenArena LLM workflow...",
    "🔗 Connecting to OpenArena: ws://opencw02ke.execute-api.us-east-1.amazonaws.com/prod",
    "📤 Sending query to Azure OpenAI Embeddings",
    "🗄️ Text vectorization using text-embedding-ada-002",
    "🔍 Creating semantic vectors for similarity matching...",
    "📝 LLM response received: 2,640 characters of structured JSON",
    "⚡ Extracting work item data for embedding generation...",
    "📅 Creating 1536-dimensional semantic embeddings..."
  ],

  // Phase 3: Embedding Generation (4 messages)
  phase3: [
    "🧮 Creating high-dimensional semantic embeddings...",
    "📐 Normalizing embeddings for cosine similarity...",
    "🤖 Generated high-quality semantic embeddings",
    "🚀 Embedding generation completed in 0.01 seconds"
  ],

  // Phase 4: Vector Database (6 messages)
  phase4: [
    "🤖 Preparing embeddings for vector database storage...",
    "📊 Initializing FAISS vector index with 1536 dimensions...",
    "💾 Storing work items in vector database...",
    "🗄️ Saved FAISS index with vectors (includes metadata)",
    "🔍 Performing vector similarity search with 0.85 threshold...",
    "⚡ Using selected work item as query vector..."
  ],

  // Phase 5: Vector Similarity Search (6 messages)
  phase5: [
    "📤 Computing cosine similarity between embeddings...",
    "🧮 Ranking results by semantic similarity score...",
    "🔍 Filtering results above 85% similarity threshold...",
    "📊 Applying relevance scoring and ranking...",
    "✅ Vector similarity search completed successfully",
    "🎯 Semantic analysis complete!"
  ],

  // Phase 6: Results (0 messages - will be handled by completion)
  phase6: []
};

// Phase configuration with timing and message counts
export const PHASE_CONFIG = {
  phase1: { name: "ADO Search & System Prompt Creation", messageCount: 4, duration: 4, progressPercent: 20 },
  phase2: { name: "LLM Analysis & Response Processing", messageCount: 8, duration: 8, progressPercent: 20 },
  phase3: { name: "Embedding Generation", messageCount: 4, duration: 4, progressPercent: 20 },
  phase4: { name: "Vector Database", messageCount: 6, duration: 6, progressPercent: 20 },
  phase5: { name: "Vector Similarity Search", messageCount: 6, duration: 0, progressPercent: 20 }, // Dynamic timing
  phase6: { name: "Completion", messageCount: 0, duration: 0, progressPercent: 0 }
};

// Timing configuration
export const TIMING_CONFIG = {
  totalDuration: 60, // 1 minute in seconds (but phases 1-4 complete in 22s)
  messageInterval: 1, // 1 second per message for phases 1-4
  totalMessages: 28,
  phase1to4Duration: 120, // Phases 1-4 complete in 2 minutes total
  phase5Dynamic: true // Phase 5 waits for actual completion
};

// Helper function to get all messages in sequence
export const getAllMessages = () => {
  const allMessages = [];
  Object.values(LOADING_MESSAGES).forEach(phaseMessages => {
    allMessages.push(...phaseMessages);
  });
  return allMessages;
};

// Helper function to get messages for a specific phase
export const getPhaseMessages = (phaseNumber) => {
  const phaseKey = `phase${phaseNumber}`;
  return LOADING_MESSAGES[phaseKey] || [];
};

// Helper function to get phase configuration
export const getPhaseConfig = (phaseNumber) => {
  const phaseKey = `phase${phaseNumber}`;
  return PHASE_CONFIG[phaseKey] || null;
};

// Helper function to calculate progress percentage based on phase completion
export const calculateProgress = (currentMessageIndex) => {
  const currentPhase = getCurrentPhase(currentMessageIndex);
  
  // Simple linear progress: 20% per phase, with smooth progression within each phase
  const baseProgress = (currentPhase - 1) * 20; // 0%, 20%, 40%, 60%, 80%
  
  // Calculate progress within current phase (0-20%)
  let cumulativeMessages = 0;
  for (let phase = 1; phase < currentPhase; phase++) {
    cumulativeMessages += getPhaseConfig(phase).messageCount;
  }
  
  const phaseMessageIndex = currentMessageIndex - cumulativeMessages;
  const phaseConfig = getPhaseConfig(currentPhase);
  const phaseProgress = Math.round((phaseMessageIndex / phaseConfig.messageCount) * 20);
  
  const totalProgress = Math.min(100, baseProgress + phaseProgress);
  
  console.log(`📊 Progress calculation: phase=${currentPhase}, base=${baseProgress}%, phaseProgress=${phaseProgress}%, total=${totalProgress}%`);
  
  return totalProgress;
};

// Helper function to get current phase based on message index
export const getCurrentPhase = (messageIndex) => {
  let cumulativeMessages = 0;
  for (let phase = 1; phase <= 6; phase++) {
    const phaseConfig = getPhaseConfig(phase);
    if (messageIndex < cumulativeMessages + phaseConfig.messageCount) {
      return phase;
    }
    cumulativeMessages += phaseConfig.messageCount;
  }
  return 6; // Default to last phase
};

// Helper function to get phase progress within current phase
export const getPhaseProgress = (messageIndex) => {
  const currentPhase = getCurrentPhase(messageIndex);
  const phaseConfig = getPhaseConfig(currentPhase);
  
  let cumulativeMessages = 0;
  for (let phase = 1; phase < currentPhase; phase++) {
    cumulativeMessages += getPhaseConfig(phase).messageCount;
  }
  
  const phaseMessageIndex = messageIndex - cumulativeMessages;
  return Math.round((phaseMessageIndex / phaseConfig.messageCount) * 100);
};

// Helper function to get message interval for a specific phase
export const getPhaseMessageInterval = (phaseNumber) => {
  const phaseConfig = getPhaseConfig(phaseNumber);
  if (!phaseConfig) return TIMING_CONFIG.messageInterval;
  
  // For phases 1-4, use 1 second per message
  if (phaseNumber >= 1 && phaseNumber <= 4) {
    return 1; // 1 second per message
  }
  
  // Phase 5 uses dynamic timing
  if (phaseNumber === 5) {
    return 2; // Slower for waiting messages, will be overridden for completion messages
  }
  
  return TIMING_CONFIG.messageInterval;
};

// Helper function to determine if phase 5 should show completion messages
export const shouldShowPhase5Completion = (hasResults = false) => {
  return hasResults;
};

// Get phase 5 completion messages (last 2 messages)
export const getPhase5CompletionMessages = () => {
  const phase5Messages = getPhaseMessages(5);
  return phase5Messages.slice(-2); // Last 2 messages
};

// Get phase 5 waiting messages (first 4 messages)
export const getPhase5WaitingMessages = () => {
  const phase5Messages = getPhaseMessages(5);
  return phase5Messages.slice(0, -2); // All but last 2 messages
};

// Enhanced real-time updates function with phase-based timing
export const createEnhancedRealTimeUpdates = (updateCallback, onComplete = null) => {
  let messageIndex = 0;
  let intervalId = null;
  let phase5CompletionTriggered = false;
  let lastPhase = 0; // Track last phase to prevent flickering
  let lastProgress = 0; // Track last progress to ensure monotonic increase
  
  const allMessages = getAllMessages();
  
  const updateProgress = () => {
    const phase = getCurrentPhase(messageIndex);
    const progress = calculateProgress(messageIndex);
    const phaseProgress = getPhaseProgress(messageIndex);
    
    // Initialize lastPhase and lastProgress on first run
    if (messageIndex === 0) {
      lastPhase = phase;
      lastProgress = progress;
    }
    
    // Ensure phase only moves forward (no flickering)
    const stablePhase = Math.max(phase, lastPhase);
    lastPhase = stablePhase;
    
    // Ensure progress only increases (no decreasing)
    const stableProgress = Math.max(progress, lastProgress);
    lastProgress = stableProgress;
    
    console.log(`🔄 Update: messageIndex=${messageIndex}, phase=${phase}→${stablePhase}, progress=${progress}%→${stableProgress}%`);
    
    updateCallback({
      messageIndex,
      currentPhase: stablePhase,
      message: allMessages[messageIndex],
      progress: stableProgress,
      phaseProgress,
      totalMessages: allMessages.length
    });
  };
  
  const scheduleNextMessage = () => {
    const phase = getCurrentPhase(messageIndex);
    const interval = getPhaseMessageInterval(phase) * 1000; // Convert to milliseconds
    
    intervalId = setTimeout(() => {
      if (messageIndex < allMessages.length) {
        updateProgress();
        messageIndex++;
        
        // Check if we're in phase 5 and should wait for completion
        const newPhase = getCurrentPhase(messageIndex);
        if (newPhase === 5 && !phase5CompletionTriggered) {
          const phase5WaitingMsgs = getPhase5WaitingMessages();
          const phase5MessageIndex = messageIndex - 22; // Phase 5 starts after 22 messages
          
          if (phase5MessageIndex < phase5WaitingMsgs.length) {
            // Continue with phase 5 waiting messages
            scheduleNextMessage();
          } else {
            // Stop and wait for external trigger to show completion messages
            console.log('⏸️ Phase 5 waiting for completion trigger...');
            return;
          }
        } else {
          scheduleNextMessage();
        }
      } else if (onComplete) {
        console.log('✅ All messages completed, calling onComplete');
        onComplete();
      }
    }, interval);
  };
  
  const start = () => {
    // Reset all tracking variables
    messageIndex = 0;
    lastPhase = 0;
    lastProgress = 0;
    phase5CompletionTriggered = false;
    
    // Clear any existing interval
    if (intervalId) {
      clearTimeout(intervalId);
      intervalId = null;
    }
    
    // Start with first message
    updateProgress();
    messageIndex++;
    scheduleNextMessage();
  };
  
  const stop = () => {
    if (intervalId) {
      clearTimeout(intervalId);
      intervalId = null;
    }
  };
  
  const triggerPhase5Completion = () => {
    if (getCurrentPhase(messageIndex) === 5 && !phase5CompletionTriggered) {
      phase5CompletionTriggered = true;
      
      // Ensure we're at phase 5 and progress is at least 80%
      lastPhase = 5;
      lastProgress = Math.max(lastProgress, 80);
      
      // Show completion messages quickly
      const completionMessages = getPhase5CompletionMessages();
      let completionIndex = 0;
      
      const showCompletionMessage = () => {
        if (completionIndex < completionMessages.length) {
          const completionProgress = 90 + (completionIndex + 1) * 5; // 90%, 95%, 100%
          const stableProgress = Math.max(completionProgress, lastProgress);
          lastProgress = stableProgress;
          
          console.log(`🎯 Phase 5 completion: message ${completionIndex + 1}/${completionMessages.length}, progress=${stableProgress}%`);
          
          updateCallback({
            messageIndex: messageIndex + completionIndex,
            currentPhase: 5,
            message: completionMessages[completionIndex],
            progress: stableProgress,
            phaseProgress: 80 + (completionIndex + 1) * 10, // Quick phase progress
            totalMessages: allMessages.length
          });
          
          completionIndex++;
          if (completionIndex < completionMessages.length) {
            setTimeout(showCompletionMessage, 500); // 0.5 seconds between completion messages
          } else if (onComplete) {
            setTimeout(onComplete, 500);
          }
        }
      };
      
      showCompletionMessage();
    }
  };
  
  return {
    start,
    stop,
    triggerPhase5Completion,
    getCurrentProgress: () => calculateProgress(messageIndex),
    getCurrentPhase: () => getCurrentPhase(messageIndex)
  };
};

const loadingMessagesConfig = {
  LOADING_MESSAGES,
  PHASE_CONFIG,
  TIMING_CONFIG,
  getAllMessages,
  getPhaseMessages,
  getPhaseConfig,
  calculateProgress,
  getCurrentPhase,
  getPhaseProgress,
  getPhaseMessageInterval,
  shouldShowPhase5Completion,
  getPhase5CompletionMessages,
  getPhase5WaitingMessages,
  createEnhancedRealTimeUpdates
};

export default loadingMessagesConfig;
