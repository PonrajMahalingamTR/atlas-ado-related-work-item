import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  LinearProgress,
  Fade,
  Chip,
  Avatar,
  Stack,
  CircularProgress
} from '@mui/material';
import {
  Psychology as AIIcon,
  Search as SearchIcon,
  DataObject as DataIcon,
  CloudDone as CloudIcon,
  AutoAwesome as SparkleIcon,
  Speed as SpeedIcon,
  CheckCircle as CheckIcon,
  HourglassEmpty as HourglassIcon,
  Settings as SettingsIcon,
  Storage as StorageIcon,
  Memory as MemoryIcon,
  CloudQueue as CloudQueueIcon,
  Lightbulb as LightbulbIcon,
  Cached as CachedIcon,
  TrendingUp as TrendingUpIcon,
  Build as BuildIcon,
  Science as ScienceIcon,
  FindInPage as FindInPageIcon,
  SmartToy as SmartToyIcon,
  Storage as DatabaseIcon
} from '@mui/icons-material';

/**
 * Semantic AI Progress Bar - Dedicated component for AI Deep Dive analysis
 * 
 * This component shows a 5-phase progress bar for semantic similarity analysis:
 * Phase 1: ADO Search & System Prompt Creation
 * Phase 2: LLM Analysis & Response Processing
 * Phase 3: Embedding Generation
 * Phase 4: Vector Database
 * Phase 5: Vector Similarity Search
 */
const SemanticAIProgressBar = ({ 
  isRunning, 
  progress = 0, 
  currentStep = 0, 
  totalSteps = 5, 
  estimatedTime = '1-2 minutes',
  costInfo,
  realTimeMessage = null,
  currentModel = 'Claude 4.1 Opus',
  iconType = 1, // 1-10 different AI icon types
  cycleIcons = false, // Enable cycling through all icons
  currentPhase = 1, // NEW: Current phase from enhanced updates
  phaseProgress = 0 // NEW: Phase progress from enhanced updates
}) => {
  // Use raw progress value with CSS transitions for smooth animation
  const [throttledProgress, setThrottledProgress] = useState(0);
  
  // Throttle progress updates to prevent rapid changes
  useEffect(() => {
    if (isRunning) {
      const timeoutId = setTimeout(() => {
        setThrottledProgress(progress);
      }, 100); // 100ms throttle
      
      return () => clearTimeout(timeoutId);
    } else {
      setThrottledProgress(0);
    }
  }, [progress, isRunning]);
  
  console.log('🌟 SemanticAIProgressBar rendered with props:', {
    isRunning,
    progress,
    currentPhase,
    phaseProgress,
    realTimeMessage,
    timestamp: new Date().toISOString()
  });

  const [currentIconType, setCurrentIconType] = React.useState(iconType);
  const [messageIndex, setMessageIndex] = React.useState(0);

  // Semantic AI Deep Dive Messages for each phase
  const semanticMessages = {
    phase1: [
      "🤖 Initializing Azure DevOps search for work item...",
      "⚡ Successfully retrieved related work items with expanded fields",
      "🧠 Preparing system prompt for AI analysis...",
      "📝 Creating structured embedding generation prompt..."
    ],
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
    phase3: [
      "🧮 Creating high-dimensional semantic embeddings...",
      "📐 Normalizing embeddings for cosine similarity...",
      "🤖 Generated high-quality semantic embeddings",
      "🚀 Embedding generation completed in 0.01 seconds"
    ],
    phase4: [
      "🤖 Preparing embeddings for vector database storage...",
      "📊 Initializing FAISS vector index with 1536 dimensions...",
      "💾 Storing work items in vector database...",
      "🗄️ Saved FAISS index with vectors (includes metadata)",
      "🔍 Performing vector similarity search with 0.85 threshold...",
      "⚡ Using selected work item as query vector..."
    ],
    phase5: [
      "📤 Computing cosine similarity between embeddings...",
      "🧮 Ranking results by semantic similarity score...",
      "🔍 Filtering results above 85% similarity threshold...",
      "📊 Applying relevance scoring and ranking...",
      "✅ Vector similarity search completed successfully",
      "🎯 Semantic analysis complete!"
    ]
  };

  // Phase configuration with timing
  const phaseConfig = {
    phase1: { name: "ADO Search & System Prompt Creation", duration: 20, messageCount: 4 },
    phase2: { name: "LLM Analysis & Response Processing", duration: 40, messageCount: 8 },
    phase3: { name: "Embedding Generation", duration: 20, messageCount: 4 },
    phase4: { name: "Vector Database", duration: 30, messageCount: 6 },
    phase5: { name: "Vector Similarity Search", duration: 10, messageCount: 6 }
  };

  // Get all messages in sequence
  const getAllMessages = () => {
    return [
      ...semanticMessages.phase1,
      ...semanticMessages.phase2,
      ...semanticMessages.phase3,
      ...semanticMessages.phase4,
      ...semanticMessages.phase5
    ];
  };

  // Calculate which phase we're in based on message index
  const getCurrentPhaseFromIndex = (msgIndex) => {
    let currentIndex = 0;
    for (let i = 1; i <= 5; i++) {
      const phaseKey = `phase${i}`;
      const phaseLength = semanticMessages[phaseKey].length;
      if (msgIndex < currentIndex + phaseLength) {
        return i;
      }
      currentIndex += phaseLength;
    }
    return 5;
  };

  // Calculate progress within current phase
  const getPhaseProgressFromIndex = (msgIndex) => {
    let currentIndex = 0;
    for (let i = 1; i <= 5; i++) {
      const phaseKey = `phase${i}`;
      const phaseLength = semanticMessages[phaseKey].length;
      if (msgIndex < currentIndex + phaseLength) {
        const phasePosition = msgIndex - currentIndex;
        return (phasePosition / phaseLength) * 100;
      }
      currentIndex += phaseLength;
    }
    return 100;
  };

  // NOTE: Removed internal timing logic - now using props from enhanced real-time updates
  // The currentPhase, phaseProgress, and realTimeMessage are now passed as props

  // Cycle through icons when cycleIcons is enabled
  React.useEffect(() => {
    if (cycleIcons && isRunning) {
      const interval = setInterval(() => {
        setCurrentIconType(prev => (prev >= 10 ? 1 : prev + 1));
      }, 2000); // Change icon every 2 seconds

      return () => clearInterval(interval);
    } else {
      setCurrentIconType(iconType);
    }
  }, [cycleIcons, isRunning, iconType]);

  const getStepIcon = (stepIndex) => {
    const icons = [
      <FindInPageIcon sx={{ color: '#1976d2' }} />, // Phase 1: ADO Search & System Prompt
      <SmartToyIcon sx={{ color: '#388e3c' }} />,   // Phase 2: LLM Analysis & Response Processing
      <MemoryIcon sx={{ color: '#7b1fa2' }} />,     // Phase 3: Embedding Generation
      <DatabaseIcon sx={{ color: '#f57c00' }} />,   // Phase 4: Vector Database
      <TrendingUpIcon sx={{ color: '#d32f2f' }} />  // Phase 5: Vector Similarity Search
    ];
    return icons[stepIndex] || <HourglassIcon sx={{ color: '#757575' }} />;
  };

  const getAIIcon = () => {
    switch(currentIconType) {
      case 1: return getBrainIcon();
      case 2: return getNeuralNetworkIcon();
      case 3: return getDataFlowIcon();
      case 4: return getQuantumIcon();
      case 5: return getCircuitIcon();
      case 6: return getMatrixIcon();
      case 7: return getHologramIcon();
      case 8: return getCrystalIcon();
      case 9: return getOrbIcon();
      case 10: return getWaveIcon();
      default: return getBrainIcon();
    }
  };

  const getBrainIcon = () => (
    <Box sx={{ width: 40, height: 40, position: 'relative', animation: 'hologramPulse 2s ease-in-out infinite' }}>
      <Box sx={{ width: 32, height: 32, position: 'absolute', top: 4, left: 4, border: '1px solid rgba(255, 255, 255, 0.8)', borderRadius: '8px', animation: 'hologramGlow 2s ease-in-out infinite' }}>
        <Box sx={{ position: 'absolute', top: 8, left: 8, width: 16, height: 16, border: '1px solid rgba(255, 255, 255, 0.6)', borderRadius: '4px', animation: 'hologramInner 1.5s ease-in-out infinite' }} />
        <Box sx={{ position: 'absolute', top: 12, left: 12, width: 8, height: 8, bgcolor: 'rgba(255, 255, 255, 0.4)', borderRadius: '2px', animation: 'hologramCore 1s ease-in-out infinite' }} />
      </Box>
      <Box sx={{ position: 'absolute', top: 0, left: 8, width: 24, height: 2, bgcolor: 'rgba(255, 255, 255, 0.8)', animation: 'hologramScan 2s ease-in-out infinite' }} />
    </Box>
  );

  const getNeuralNetworkIcon = () => (
    <Box sx={{ width: 40, height: 40, position: 'relative', animation: 'neuralNetworkPulse 2s ease-in-out infinite' }}>
      <Box sx={{ width: 36, height: 36, position: 'absolute', top: 2, left: 2 }}>
        {/* Neural nodes */}
        <Box sx={{ position: 'absolute', top: 4, left: 8, width: 6, height: 6, bgcolor: '#4caf50', borderRadius: '50%', animation: 'nodePulse 1s ease-in-out infinite' }} />
        <Box sx={{ position: 'absolute', top: 12, right: 6, width: 4, height: 4, bgcolor: '#ff9800', borderRadius: '50%', animation: 'nodePulse 1s ease-in-out infinite 0.3s' }} />
        <Box sx={{ position: 'absolute', bottom: 8, left: 4, width: 5, height: 5, bgcolor: '#9c27b0', borderRadius: '50%', animation: 'nodePulse 1s ease-in-out infinite 0.6s' }} />
        <Box sx={{ position: 'absolute', bottom: 4, right: 8, width: 4, height: 4, bgcolor: '#00bcd4', borderRadius: '50%', animation: 'nodePulse 1s ease-in-out infinite 0.9s' }} />
        <Box sx={{ position: 'absolute', top: 18, left: '50%', transform: 'translateX(-50%)', width: 6, height: 6, bgcolor: '#e91e63', borderRadius: '50%', animation: 'nodePulse 1s ease-in-out infinite 1.2s' }} />
        
        {/* Neural connections */}
        <Box sx={{ position: 'absolute', top: 7, left: 11, width: 12, height: 1, bgcolor: 'rgba(76, 175, 80, 0.6)', transform: 'rotate(45deg)', animation: 'connectionPulse 1.5s ease-in-out infinite' }} />
        <Box sx={{ position: 'absolute', top: 15, left: 8, width: 8, height: 1, bgcolor: 'rgba(255, 152, 0, 0.6)', transform: 'rotate(-30deg)', animation: 'connectionPulse 1.5s ease-in-out infinite 0.5s' }} />
        <Box sx={{ position: 'absolute', bottom: 10, left: 7, width: 10, height: 1, bgcolor: 'rgba(156, 39, 176, 0.6)', transform: 'rotate(60deg)', animation: 'connectionPulse 1.5s ease-in-out infinite 1s' }} />
      </Box>
    </Box>
  );

  const getDataFlowIcon = () => (
    <Box sx={{ width: 40, height: 40, position: 'relative', animation: 'dataFlowPulse 2s ease-in-out infinite' }}>
      <Box sx={{ width: 32, height: 32, position: 'absolute', top: 4, left: 4, border: '2px solid rgba(255,255,255,0.3)', borderRadius: '50%', animation: 'dataFlowRotate 3s linear infinite' }}>
        <Box sx={{ position: 'absolute', top: -2, left: '50%', transform: 'translateX(-50%)', width: 4, height: 4, bgcolor: '#4caf50', borderRadius: '50%', animation: 'dataFlowMove 2s ease-in-out infinite' }} />
        <Box sx={{ position: 'absolute', right: -2, top: '50%', transform: 'translateY(-50%)', width: 3, height: 3, bgcolor: '#ff9800', borderRadius: '50%', animation: 'dataFlowMove 2s ease-in-out infinite 0.5s' }} />
        <Box sx={{ position: 'absolute', bottom: -2, left: '50%', transform: 'translateX(-50%)', width: 3, height: 3, bgcolor: '#9c27b0', borderRadius: '50%', animation: 'dataFlowMove 2s ease-in-out infinite 1s' }} />
        <Box sx={{ position: 'absolute', left: -2, top: '50%', transform: 'translateY(-50%)', width: 3, height: 3, bgcolor: '#00bcd4', borderRadius: '50%', animation: 'dataFlowMove 2s ease-in-out infinite 1.5s' }} />
      </Box>
    </Box>
  );

  const getQuantumIcon = () => (
    <Box sx={{ width: 40, height: 40, position: 'relative', animation: 'quantumPulse 2s ease-in-out infinite' }}>
      <Box sx={{ width: 24, height: 24, position: 'absolute', top: 8, left: 8, border: '2px solid rgba(255,255,255,0.5)', borderRadius: '50%', animation: 'quantumRotate 4s linear infinite' }}>
        <Box sx={{ position: 'absolute', top: -1, left: '50%', transform: 'translateX(-50%)', width: 2, height: 2, bgcolor: '#4caf50', borderRadius: '50%', animation: 'quantumGlow 1s ease-in-out infinite' }} />
        <Box sx={{ position: 'absolute', right: -1, top: '50%', transform: 'translateY(-50%)', width: 2, height: 2, bgcolor: '#ff9800', borderRadius: '50%', animation: 'quantumGlow 1s ease-in-out infinite 0.25s' }} />
        <Box sx={{ position: 'absolute', bottom: -1, left: '50%', transform: 'translateX(-50%)', width: 2, height: 2, bgcolor: '#9c27b0', borderRadius: '50%', animation: 'quantumGlow 1s ease-in-out infinite 0.5s' }} />
        <Box sx={{ position: 'absolute', left: -1, top: '50%', transform: 'translateY(-50%)', width: 2, height: 2, bgcolor: '#00bcd4', borderRadius: '50%', animation: 'quantumGlow 1s ease-in-out infinite 0.75s' }} />
      </Box>
      <Box sx={{ position: 'absolute', top: 18, left: 18, width: 4, height: 4, bgcolor: 'rgba(255,255,255,0.8)', borderRadius: '50%', animation: 'quantumCenter 2s ease-in-out infinite' }} />
    </Box>
  );

  const getCircuitIcon = () => (
    <Box sx={{ width: 40, height: 40, position: 'relative', animation: 'circuitPulse 2s ease-in-out infinite' }}>
      <Box sx={{ width: 36, height: 36, position: 'absolute', top: 2, left: 2 }}>
        {/* Circuit lines */}
        <Box sx={{ position: 'absolute', top: 8, left: 4, width: 12, height: 2, bgcolor: '#4caf50', borderRadius: '1px', animation: 'circuitFlow 1.5s ease-in-out infinite' }} />
        <Box sx={{ position: 'absolute', top: 16, right: 4, width: 2, height: 8, bgcolor: '#ff9800', borderRadius: '1px', animation: 'circuitFlow 1.5s ease-in-out infinite 0.3s' }} />
        <Box sx={{ position: 'absolute', bottom: 8, left: 6, width: 10, height: 2, bgcolor: '#9c27b0', borderRadius: '1px', animation: 'circuitFlow 1.5s ease-in-out infinite 0.6s' }} />
        <Box sx={{ position: 'absolute', top: 12, left: 8, width: 2, height: 6, bgcolor: '#00bcd4', borderRadius: '1px', animation: 'circuitFlow 1.5s ease-in-out infinite 0.9s' }} />
        
        {/* Circuit nodes */}
        <Box sx={{ position: 'absolute', top: 6, left: 4, width: 4, height: 4, bgcolor: '#4caf50', borderRadius: '50%', animation: 'circuitNode 1s ease-in-out infinite' }} />
        <Box sx={{ position: 'absolute', top: 14, right: 4, width: 3, height: 3, bgcolor: '#ff9800', borderRadius: '50%', animation: 'circuitNode 1s ease-in-out infinite 0.2s' }} />
        <Box sx={{ position: 'absolute', bottom: 6, left: 6, width: 3, height: 3, bgcolor: '#9c27b0', borderRadius: '50%', animation: 'circuitNode 1s ease-in-out infinite 0.4s' }} />
        <Box sx={{ position: 'absolute', top: 10, left: 8, width: 3, height: 3, bgcolor: '#00bcd4', borderRadius: '50%', animation: 'circuitNode 1s ease-in-out infinite 0.6s' }} />
      </Box>
    </Box>
  );

  const getMatrixIcon = () => (
    <Box sx={{ width: 40, height: 40, position: 'relative', animation: 'matrixPulse 2s ease-in-out infinite' }}>
      <Box sx={{ width: 36, height: 36, position: 'absolute', top: 2, left: 2 }}>
        {/* Matrix grid */}
        {Array.from({ length: 6 }, (_, i) => (
          <Box key={i} sx={{ position: 'absolute', top: i * 6, left: 0, width: 36, height: 1, bgcolor: 'rgba(76, 175, 80, 0.3)', animation: `matrixLine${i} 2s ease-in-out infinite ${i * 0.2}s` }} />
        ))}
        {Array.from({ length: 6 }, (_, i) => (
          <Box key={i} sx={{ position: 'absolute', top: 0, left: i * 6, width: 1, height: 36, bgcolor: 'rgba(76, 175, 80, 0.3)', animation: `matrixColumn${i} 2s ease-in-out infinite ${i * 0.2}s` }} />
        ))}
        
        {/* Matrix data points */}
        <Box sx={{ position: 'absolute', top: 8, left: 8, width: 2, height: 2, bgcolor: '#4caf50', animation: 'matrixData 1s ease-in-out infinite' }} />
        <Box sx={{ position: 'absolute', top: 14, left: 20, width: 2, height: 2, bgcolor: '#4caf50', animation: 'matrixData 1s ease-in-out infinite 0.2s' }} />
        <Box sx={{ position: 'absolute', top: 20, left: 12, width: 2, height: 2, bgcolor: '#4caf50', animation: 'matrixData 1s ease-in-out infinite 0.4s' }} />
        <Box sx={{ position: 'absolute', top: 26, left: 24, width: 2, height: 2, bgcolor: '#4caf50', animation: 'matrixData 1s ease-in-out infinite 0.6s' }} />
      </Box>
    </Box>
  );

  const getHologramIcon = () => (
    <Box sx={{ width: 40, height: 40, position: 'relative', animation: 'hologramPulse 2s ease-in-out infinite' }}>
      <Box sx={{ width: 32, height: 32, position: 'absolute', top: 4, left: 4, border: '1px solid rgba(255, 255, 255, 0.8)', borderRadius: '8px', animation: 'hologramGlow 2s ease-in-out infinite' }}>
        <Box sx={{ position: 'absolute', top: 8, left: 8, width: 16, height: 16, border: '1px solid rgba(255, 255, 255, 0.6)', borderRadius: '4px', animation: 'hologramInner 1.5s ease-in-out infinite' }} />
        <Box sx={{ position: 'absolute', top: 12, left: 12, width: 8, height: 8, bgcolor: 'rgba(255, 255, 255, 0.4)', borderRadius: '2px', animation: 'hologramCore 1s ease-in-out infinite' }} />
      </Box>
      <Box sx={{ position: 'absolute', top: 0, left: 8, width: 24, height: 2, bgcolor: 'rgba(255, 255, 255, 0.8)', animation: 'hologramScan 2s ease-in-out infinite' }} />
    </Box>
  );

  const getCrystalIcon = () => (
    <Box sx={{ width: 40, height: 40, position: 'relative', animation: 'crystalPulse 2s ease-in-out infinite' }}>
      <Box sx={{ width: 24, height: 32, position: 'absolute', top: 4, left: 8, bgcolor: 'rgba(156, 39, 176, 0.8)', clipPath: 'polygon(50% 0%, 0% 100%, 100% 100%)', animation: 'crystalGlow 2s ease-in-out infinite' }}>
        <Box sx={{ position: 'absolute', top: 8, left: '50%', transform: 'translateX(-50%)', width: 8, height: 16, bgcolor: 'rgba(255, 255, 255, 0.3)', clipPath: 'polygon(50% 0%, 0% 100%, 100% 100%)', animation: 'crystalInner 1.5s ease-in-out infinite' }} />
      </Box>
      <Box sx={{ position: 'absolute', top: 8, left: 6, width: 2, height: 2, bgcolor: '#9c27b0', borderRadius: '50%', animation: 'crystalParticle 1s ease-in-out infinite' }} />
      <Box sx={{ position: 'absolute', top: 16, right: 6, width: 2, height: 2, bgcolor: '#9c27b0', borderRadius: '50%', animation: 'crystalParticle 1s ease-in-out infinite 0.3s' }} />
      <Box sx={{ position: 'absolute', bottom: 8, left: 8, width: 2, height: 2, bgcolor: '#9c27b0', borderRadius: '50%', animation: 'crystalParticle 1s ease-in-out infinite 0.6s' }} />
    </Box>
  );

  const getOrbIcon = () => (
    <Box sx={{ width: 40, height: 40, position: 'relative', animation: 'orbPulse 2s ease-in-out infinite' }}>
      <Box sx={{ width: 32, height: 32, position: 'absolute', top: 4, left: 4, bgcolor: 'rgba(255, 255, 255, 0.1)', borderRadius: '50%', border: '2px solid rgba(255, 255, 255, 0.3)', animation: 'orbGlow 3s ease-in-out infinite' }}>
        <Box sx={{ position: 'absolute', top: 8, left: 8, width: 16, height: 16, bgcolor: 'rgba(25, 118, 210, 0.3)', borderRadius: '50%', animation: 'orbInner 2s ease-in-out infinite' }} />
        <Box sx={{ position: 'absolute', top: 12, left: 12, width: 8, height: 8, bgcolor: 'rgba(25, 118, 210, 0.6)', borderRadius: '50%', animation: 'orbCore 1s ease-in-out infinite' }} />
      </Box>
      <Box sx={{ position: 'absolute', top: 2, left: 8, width: 3, height: 3, bgcolor: '#1976d2', borderRadius: '50%', animation: 'orbParticle 2s ease-in-out infinite' }} />
      <Box sx={{ position: 'absolute', top: 8, right: 6, width: 2, height: 2, bgcolor: '#1976d2', borderRadius: '50%', animation: 'orbParticle 2s ease-in-out infinite 0.5s' }} />
      <Box sx={{ position: 'absolute', bottom: 6, left: 6, width: 2, height: 2, bgcolor: '#1976d2', borderRadius: '50%', animation: 'orbParticle 2s ease-in-out infinite 1s' }} />
    </Box>
  );

  const getWaveIcon = () => (
    <Box sx={{ width: 40, height: 40, position: 'relative', animation: 'wavePulse 2s ease-in-out infinite' }}>
      <Box sx={{ position: 'absolute', top: 8, left: 4, width: 32, height: 2, bgcolor: '#4caf50', borderRadius: '1px', animation: 'wave1 1.5s ease-in-out infinite' }} />
      <Box sx={{ position: 'absolute', top: 14, left: 4, width: 32, height: 2, bgcolor: '#ff9800', borderRadius: '1px', animation: 'wave2 1.5s ease-in-out infinite 0.2s' }} />
      <Box sx={{ position: 'absolute', top: 20, left: 4, width: 32, height: 2, bgcolor: '#9c27b0', borderRadius: '1px', animation: 'wave3 1.5s ease-in-out infinite 0.4s' }} />
      <Box sx={{ position: 'absolute', top: 26, left: 4, width: 32, height: 2, bgcolor: '#00bcd4', borderRadius: '1px', animation: 'wave4 1.5s ease-in-out infinite 0.6s' }} />
      
      <Box sx={{ position: 'absolute', top: 6, left: 8, width: 2, height: 2, bgcolor: '#4caf50', borderRadius: '50%', animation: 'waveData 1s ease-in-out infinite' }} />
      <Box sx={{ position: 'absolute', top: 12, right: 8, width: 2, height: 2, bgcolor: '#ff9800', borderRadius: '50%', animation: 'waveData 1s ease-in-out infinite 0.3s' }} />
      <Box sx={{ position: 'absolute', top: 18, left: 12, width: 2, height: 2, bgcolor: '#9c27b0', borderRadius: '50%', animation: 'waveData 1s ease-in-out infinite 0.6s' }} />
      <Box sx={{ position: 'absolute', top: 24, right: 12, width: 2, height: 2, bgcolor: '#00bcd4', borderRadius: '50%', animation: 'waveData 1s ease-in-out infinite 0.9s' }} />
    </Box>
  );

  const getStepStatus = (stepIndex) => {
    const stepNumber = stepIndex + 1; // Convert 0-based to 1-based
    
    if (stepNumber < currentPhase) return 'completed';
    if (stepNumber === currentPhase) return 'active';
    return 'pending';
  };

  const steps = [
    { 
      title: 'ADO Search & System Prompt Creation', 
      description: 'Initializing Azure DevOps search and preparing AI prompts',
      icon: 0
    },
    {
      title: 'LLM Analysis & Response Processing',
      description: 'Processing through OpenArena LLM workflow and extracting data',
      icon: 1
    },
    { 
      title: 'Embedding Generation', 
      description: 'Creating high-dimensional semantic embeddings',
      icon: 2
    },
    {
      title: 'Vector Database',
      description: 'Storing embeddings and initializing vector search',
      icon: 3
    },
    { 
      title: 'Vector Similarity Search', 
      description: 'Computing similarity scores and ranking results',
      icon: 4
    }
  ];

  if (!isRunning) {
    console.log('⚠️ SemanticAIProgressBar not rendering - isRunning is false');
    return null;
  }

  console.log('✅ SemanticAIProgressBar is rendering - isRunning is true');

  // Get current message
  const allMessages = getAllMessages();
  const currentMessage = realTimeMessage || allMessages[messageIndex] || 'Processing...';

  return (
    <Fade in={isRunning} timeout={500}>
      <Paper 
        elevation={8} 
        sx={{ 
          p: 3, 
          mb: 3, 
          background: 'linear-gradient(135deg, #1e3a8a 0%, #6366f1 50%, #8b5cf6 100%)',
          color: 'white',
          borderRadius: 3,
          position: 'relative',
          overflow: 'hidden'
        }}
      >
        {/* Animated background pattern */}
        <Box
          sx={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: `
              radial-gradient(circle at 20% 50%, rgba(255,255,255,0.1) 0%, transparent 50%),
              radial-gradient(circle at 80% 20%, rgba(255,255,255,0.1) 0%, transparent 50%),
              radial-gradient(circle at 40% 80%, rgba(255,255,255,0.1) 0%, transparent 50%)
            `,
            animation: 'pulse 3s ease-in-out infinite'
          }}
        />
        
        <Box sx={{ position: 'relative', zIndex: 1 }}>
          {/* Header */}
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            <Box
              sx={{
                mr: 2,
                width: 48,
                height: 48,
                position: 'relative',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}
            >
              {/* AI Processor/Chip Graphics */}
              <Box
                sx={{
                  width: 40,
                  height: 40,
                  position: 'relative',
                  transition: 'all 0.5s ease-in-out',
                  transform: cycleIcons ? 'scale(1.05)' : 'scale(1)'
                }}
              >
                <Box
                  sx={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: '100%',
                    height: '100%',
                    opacity: 1,
                    transition: 'opacity 0.3s ease-in-out',
                    animation: cycleIcons ? 'iconCycle 0.3s ease-in-out' : 'none'
                  }}
                >
                  {getAIIcon()}
                </Box>
              </Box>
            </Box>
            <Box sx={{ flex: 1 }}>
              <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 0.5 }}>
                AI Intelligence Engine
              </Typography>
              <Typography variant="body2" sx={{ opacity: 0.9, mb: 0.5 }}>
                Unleashing advanced semantic analysis...
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
              <Chip 
                label={`Step ${currentPhase} of ${totalSteps}`}
                size="small"
                sx={{ 
                  bgcolor: 'rgba(255,255,255,0.2)', 
                  color: 'white', 
                  fontWeight: 'bold' 
                }}
              />
              {estimatedTime && (
                <Chip
                  icon={<HourglassIcon />}
                  label={estimatedTime}
                  size="small"
                  sx={{ 
                    bgcolor: 'rgba(255,255,255,0.2)', 
                    color: 'white',
                    '& .MuiChip-icon': { color: 'white' }
                  }}
                />
              )}
            </Box>
          </Box>

          {/* Progress Bar */}
          <Box sx={{ mb: 3 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
              <Typography variant="body2" sx={{ opacity: 0.9 }}>
                Analysis Progress
              </Typography>
              <Typography variant="body2" sx={{ opacity: 0.9 }}>
                {Math.round(throttledProgress)}%
              </Typography>
            </Box>
            <LinearProgress
              variant="determinate"
              value={throttledProgress}
              sx={{
                height: 8,
                borderRadius: 4,
                bgcolor: 'rgba(255,255,255,0.2)',
                '& .MuiLinearProgress-bar': {
                  borderRadius: 4,
                  background: 'linear-gradient(90deg, #06b6d4 0%, #3b82f6 50%, #8b5cf6 100%)',
                  transition: 'transform 0.3s ease-out' // Smooth CSS transition
                }
              }}
            />
          </Box>

          {/* Steps - Horizontal Layout */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
            {steps.map((step, index) => {
              const status = getStepStatus(index);
              const isCompleted = status === 'completed';
              const isActive = status === 'active';
              const isLast = index === steps.length - 1;
              
              return (
                <React.Fragment key={index}>
                  <Box
                    sx={{
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      p: 2,
                      borderRadius: 2,
                      bgcolor: isActive ? 'rgba(255,255,255,0.1)' : 'transparent',
                      border: isActive ? '1px solid rgba(255,255,255,0.3)' : '1px solid transparent',
                      transition: 'all 0.3s ease',
                      transform: isActive ? 'scale(1.05)' : 'scale(1)',
                      minWidth: 140,
                      textAlign: 'center',
                      position: 'relative'
                    }}
                  >
                    {/* Step Icon */}
                    <Box sx={{ mb: 1 }}>
                      {isCompleted ? (
                        <Avatar sx={{ 
                          bgcolor: '#06b6d4', 
                          width: 40, 
                          height: 40,
                          animation: 'pulse 2s ease-in-out infinite'
                        }}>
                          <CheckIcon sx={{ fontSize: 24 }} />
                        </Avatar>
                      ) : isActive ? (
                        <Avatar sx={{
                          bgcolor: '#3b82f6',
                          width: 40,
                          height: 40,
                          animation: 'aiPulse 1.5s ease-in-out infinite'
                        }}>
                          {step.icon === 0 ? (
                            <FindInPageIcon sx={{ fontSize: 24, animation: 'rotate 2s linear infinite' }} />
                          ) : step.icon === 1 ? (
                            <SmartToyIcon sx={{ fontSize: 24, animation: 'buildPulse 1.5s ease-in-out infinite' }} />
                          ) : step.icon === 2 ? (
                            <MemoryIcon sx={{ fontSize: 24, animation: 'spin 2s linear infinite' }} />
                          ) : step.icon === 3 ? (
                            <DatabaseIcon sx={{ fontSize: 24, animation: 'float 2s ease-in-out infinite' }} />
                          ) : step.icon === 4 ? (
                            <TrendingUpIcon sx={{ fontSize: 24, animation: 'flicker 1s ease-in-out infinite' }} />
                          ) : (
                            <CircularProgress
                              size={24}
                              sx={{ color: 'white' }}
                            />
                          )}
                        </Avatar>
                      ) : (
                        <Avatar sx={{ 
                          bgcolor: 'rgba(255,255,255,0.2)', 
                          width: 40, 
                          height: 40,
                          opacity: 0.6
                        }}>
                          {getStepIcon(step.icon)}
                        </Avatar>
                      )}
                    </Box>
                    
                    {/* Step Title */}
                    <Typography 
                      variant="subtitle2" 
                      sx={{ 
                        fontWeight: isActive ? 'bold' : 'normal',
                        opacity: isCompleted ? 0.8 : 1,
                        fontSize: '0.875rem',
                        mb: 0.5,
                        lineHeight: 1.2
                      }}
                    >
                      {step.title}
                    </Typography>
                    
                    {/* Step Description */}
                    <Typography 
                      variant="caption" 
                      sx={{ 
                        opacity: isActive ? 0.9 : 0.7,
                        fontSize: '0.75rem',
                        lineHeight: 1.3,
                        textAlign: 'center'
                      }}
                    >
                      {step.description}
                    </Typography>

                  </Box>
                  
                  {/* Connector Line */}
                  {!isLast && (
                    <Box
                      sx={{
                        width: 20,
                        height: 2,
                        bgcolor: isCompleted ? '#06b6d4' : 'rgba(255,255,255,0.3)',
                        borderRadius: 1,
                        transition: 'all 0.3s ease'
                      }}
                    />
                  )}
                </React.Fragment>
              );
            })}
          </Box>

          {/* Real-time Message */}
          <Box sx={{ 
            mt: 2, 
            mb: 1, 
            textAlign: 'left',
            p: 2,
            bgcolor: 'rgba(255,255,255,0.1)',
            borderRadius: 2,
            border: '1px solid rgba(255,255,255,0.2)'
          }}>
            <Typography 
              variant="body2" 
              sx={{ 
                color: 'white',
                fontWeight: 500,
                fontSize: '0.9rem',
                lineHeight: 1.4,
                animation: 'pulse 2s ease-in-out infinite'
              }}
            >
              {currentMessage}
            </Typography>
          </Box>

          {/* Footer Info */}
          <Box sx={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center', 
            mt: 2,
            pt: 1,
            borderTop: '1px solid rgba(255,255,255,0.2)'
          }}>
            <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
              {costInfo && (
                <Chip
                  icon={<SparkleIcon />}
                  label={`$${costInfo.toFixed(3)}`}
                  size="small"
                  sx={{ 
                    bgcolor: 'rgba(255,255,255,0.2)', 
                    color: 'white',
                    '& .MuiChip-icon': { color: 'white' }
                  }}
                />
              )}
            </Box>
            
            <Typography variant="caption" sx={{ opacity: 0.7 }}>
              Powered by OpenArena AI
            </Typography>
          </Box>
        </Box>

        <style jsx>{`
          @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
          }
          @keyframes pulse {
            0%, 100% { opacity: 0.5; }
            50% { opacity: 0.8; }
          }
          @keyframes aiPulse {
            0%, 100% { 
              transform: scale(1);
              box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.7);
            }
            50% { 
              transform: scale(1.1);
              box-shadow: 0 0 0 10px rgba(59, 130, 246, 0);
            }
          }
          @keyframes flicker {
            0%, 100% { opacity: 1; }
            25% { opacity: 0.5; }
            50% { opacity: 1; }
            75% { opacity: 0.7; }
          }
          @keyframes rotate {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
          }
          @keyframes buildPulse {
            0%, 100% { 
              transform: scale(1) rotate(0deg);
              opacity: 0.8;
            }
            25% { 
              transform: scale(1.1) rotate(5deg);
              opacity: 1;
            }
            50% { 
              transform: scale(1.05) rotate(0deg);
              opacity: 0.9;
            }
            75% { 
              transform: scale(1.1) rotate(-5deg);
              opacity: 1;
            }
          }
          @keyframes float {
            0%, 100% { transform: translateY(0px); }
            50% { transform: translateY(-8px); }
          }
          @keyframes brainPulse {
            0%, 100% { 
              transform: scale(1);
            }
            50% { 
              transform: scale(1.05);
            }
          }
          @keyframes brainGlow {
            0%, 100% { 
              box-shadow: 0 0 0 0 rgba(255, 255, 255, 0.3);
            }
            50% { 
              box-shadow: 0 0 15px 5px rgba(255, 255, 255, 0.6);
            }
          }
          @keyframes neuralPulse {
            0%, 100% { 
              opacity: 0.6;
              transform: scale(1);
            }
            50% { 
              opacity: 1;
              transform: scale(1.1);
            }
          }
          @keyframes neuralFlicker {
            0%, 100% { 
              opacity: 0.4;
            }
            50% { 
              opacity: 0.8;
            }
          }
          @keyframes particle1 {
            0% { 
              opacity: 0;
              transform: translateY(0px) scale(0.5);
            }
            50% { 
              opacity: 1;
              transform: translateY(-8px) scale(1);
            }
            100% { 
              opacity: 0;
              transform: translateY(-16px) scale(0.5);
            }
          }
          @keyframes particle2 {
            0% { 
              opacity: 0;
              transform: translateY(0px) scale(0.5);
            }
            50% { 
              opacity: 1;
              transform: translateY(-6px) scale(1);
            }
            100% { 
              opacity: 0;
              transform: translateY(-12px) scale(0.5);
            }
          }
          @keyframes particle3 {
            0% { 
              opacity: 0;
              transform: translateY(0px) scale(0.5);
            }
            50% { 
              opacity: 1;
              transform: translateY(-10px) scale(1);
            }
            100% { 
              opacity: 0;
              transform: translateY(-20px) scale(0.5);
            }
          }
          @keyframes particle4 {
            0% { 
              opacity: 0;
              transform: translateY(0px) scale(0.5);
            }
            50% { 
              opacity: 1;
              transform: translateY(-7px) scale(1);
            }
            100% { 
              opacity: 0;
              transform: translateY(-14px) scale(0.5);
            }
          }
          /* Neural Network Animations */
          @keyframes neuralNetworkPulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.05); }
          }
          @keyframes nodePulse {
            0%, 100% { transform: scale(1); opacity: 0.8; }
            50% { transform: scale(1.2); opacity: 1; }
          }
          @keyframes connectionPulse {
            0%, 100% { opacity: 0.6; }
            50% { opacity: 1; }
          }
          /* Data Flow Animations */
          @keyframes dataFlowPulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.05); }
          }
          @keyframes dataFlowRotate {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
          }
          @keyframes dataFlowMove {
            0%, 100% { opacity: 0.6; }
            50% { opacity: 1; }
          }
          /* Quantum Animations */
          @keyframes quantumPulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.1); }
          }
          @keyframes quantumRotate {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
          }
          @keyframes quantumGlow {
            0%, 100% { opacity: 0.6; }
            50% { opacity: 1; }
          }
          @keyframes quantumCenter {
            0%, 100% { transform: scale(1); opacity: 0.8; }
            50% { transform: scale(1.3); opacity: 1; }
          }
          /* Circuit Animations */
          @keyframes circuitPulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.05); }
          }
          @keyframes circuitFlow {
            0%, 100% { opacity: 0.6; }
            50% { opacity: 1; }
          }
          @keyframes circuitNode {
            0%, 100% { transform: scale(1); opacity: 0.8; }
            50% { transform: scale(1.2); opacity: 1; }
          }
          /* Matrix Animations */
          @keyframes matrixPulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.05); }
          }
          @keyframes matrixData {
            0%, 100% { opacity: 0.6; }
            50% { opacity: 1; }
          }
          /* Hologram Animations */
          @keyframes hologramPulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.05); }
          }
          @keyframes hologramGlow {
            0%, 100% { box-shadow: 0 0 0 0 rgba(255, 255, 255, 0.3); }
            50% { box-shadow: 0 0 10px 5px rgba(255, 255, 255, 0.6); }
          }
          @keyframes hologramInner {
            0%, 100% { opacity: 0.6; }
            50% { opacity: 1; }
          }
          @keyframes hologramCore {
            0%, 100% { opacity: 0.4; }
            50% { opacity: 0.9; }
          }
          @keyframes hologramScan {
            0% { transform: translateY(0px); opacity: 0; }
            50% { opacity: 1; }
            100% { transform: translateY(40px); opacity: 0; }
          }
          /* Crystal Animations */
          @keyframes crystalPulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.05); }
          }
          @keyframes crystalGlow {
            0%, 100% { box-shadow: 0 0 0 0 rgba(156, 39, 176, 0.3); }
            50% { box-shadow: 0 0 15px 5px rgba(156, 39, 176, 0.6); }
          }
          @keyframes crystalInner {
            0%, 100% { opacity: 0.3; }
            50% { opacity: 0.8; }
          }
          @keyframes crystalParticle {
            0%, 100% { opacity: 0.6; transform: scale(1); }
            50% { opacity: 1; transform: scale(1.2); }
          }
          /* Orb Animations */
          @keyframes orbPulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.05); }
          }
          @keyframes orbGlow {
            0%, 100% { box-shadow: 0 0 0 0 rgba(25, 118, 210, 0.3); }
            50% { box-shadow: 0 0 20px 8px rgba(25, 118, 210, 0.6); }
          }
          @keyframes orbInner {
            0%, 100% { opacity: 0.3; }
            50% { opacity: 0.8; }
          }
          @keyframes orbCore {
            0%, 100% { opacity: 0.6; }
            50% { opacity: 1; }
          }
          @keyframes orbParticle {
            0%, 100% { opacity: 0.6; transform: scale(1); }
            50% { opacity: 1; transform: scale(1.2); }
          }
          /* Wave Animations */
          @keyframes wavePulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.05); }
          }
          @keyframes wave1 {
            0%, 100% { transform: scaleX(1); opacity: 0.6; }
            50% { transform: scaleX(1.2); opacity: 1; }
          }
          @keyframes wave2 {
            0%, 100% { transform: scaleX(1); opacity: 0.6; }
            50% { transform: scaleX(1.3); opacity: 1; }
          }
          @keyframes wave3 {
            0%, 100% { transform: scaleX(1); opacity: 0.6; }
            50% { transform: scaleX(1.1); opacity: 1; }
          }
          @keyframes wave4 {
            0%, 100% { transform: scaleX(1); opacity: 0.6; }
            50% { transform: scaleX(1.4); opacity: 1; }
          }
          @keyframes waveData {
            0%, 100% { opacity: 0.6; transform: scale(1); }
            50% { opacity: 1; transform: scale(1.3); }
          }
          /* OpenArena Hologram Animations */
          @keyframes hologramPulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.05); }
          }
          @keyframes hologramGlow {
            0%, 100% { box-shadow: 0 0 0 0 rgba(255, 255, 255, 0.3); }
            50% { box-shadow: 0 0 10px 5px rgba(255, 255, 255, 0.6); }
          }
          @keyframes hologramInner {
            0%, 100% { opacity: 0.6; }
            50% { opacity: 1; }
          }
          @keyframes hologramCore {
            0%, 100% { opacity: 0.4; }
            50% { opacity: 0.9; }
          }
          @keyframes hologramScan {
            0% { transform: translateY(0px); opacity: 0; }
            50% { opacity: 1; }
            100% { transform: translateY(40px); opacity: 0; }
          }
          /* Icon Cycling Animation */
          @keyframes iconCycle {
            0% { 
              opacity: 0.7;
              transform: scale(0.95) rotateY(0deg);
            }
            50% { 
              opacity: 1;
              transform: scale(1.05) rotateY(180deg);
            }
            100% { 
              opacity: 1;
              transform: scale(1) rotateY(360deg);
            }
          }
        `}</style>
      </Paper>
    </Fade>
  );
};

export default SemanticAIProgressBar;
