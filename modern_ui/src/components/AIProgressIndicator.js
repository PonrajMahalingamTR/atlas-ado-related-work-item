import React from 'react';
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
  Science as ScienceIcon
} from '@mui/icons-material';

const AIProgressIndicator = ({ 
  isRunning, 
  progress, 
  currentStep, 
  totalSteps, 
  estimatedTime,
  costInfo,
  relatedWorkItemsCount = 0,
  realTimeMessage = null,
  currentModel = 'Claude 4 Opus',
  iconType = 1, // 1-10 different AI icon types
  cycleIcons = false // Enable cycling through all icons
}) => {
  const [currentIconType, setCurrentIconType] = React.useState(iconType);

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
      <SettingsIcon sx={{ color: '#1976d2' }} />, // Step 1: Initializing Analysis
      <BuildIcon sx={{ color: '#388e3c' }} />,  // Step 2: Generating System Prompt
      <MemoryIcon sx={{ color: '#7b1fa2' }} />,   // Step 3: AI Model Activation
      <CloudQueueIcon sx={{ color: '#f57c00' }} />, // Step 4: OpenArena Analysis
      <LightbulbIcon sx={{ color: '#d32f2f' }} />  // Step 5: Intelligence Extraction
    ];
    return icons[stepIndex] || <HourglassIcon sx={{ color: '#757575' }} />;
  };

  const getAIIcon = () => {
    switch(currentIconType) {
      case 1: return getBrainIcon(); // Current brain design
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
    <Box sx={{ width: 40, height: 40, position: 'relative', animation: 'brainPulse 2s ease-in-out infinite' }}>
      <Box sx={{ width: 32, height: 28, bgcolor: 'rgba(255,255,255,0.9)', borderRadius: '16px 16px 20px 20px', position: 'absolute', top: 6, left: '50%', transform: 'translateX(-50%)', border: '2px solid rgba(255,255,255,0.3)', animation: 'brainGlow 3s ease-in-out infinite' }}>
        <Box sx={{ position: 'absolute', top: 8, left: 8, width: 16, height: 12, border: '1px solid rgba(25, 118, 210, 0.6)', borderRadius: '8px', animation: 'neuralPulse 1.5s ease-in-out infinite' }} />
        <Box sx={{ position: 'absolute', top: 4, left: 12, width: 8, height: 4, bgcolor: 'rgba(25, 118, 210, 0.4)', borderRadius: '4px', animation: 'neuralFlicker 1s ease-in-out infinite' }} />
      </Box>
      <Box sx={{ position: 'absolute', top: 2, left: 8, width: 3, height: 3, bgcolor: '#4caf50', borderRadius: '50%', animation: 'particle1 2s ease-in-out infinite' }} />
      <Box sx={{ position: 'absolute', top: 8, right: 6, width: 2, height: 2, bgcolor: '#ff9800', borderRadius: '50%', animation: 'particle2 2.5s ease-in-out infinite 0.5s' }} />
      <Box sx={{ position: 'absolute', bottom: 4, left: 6, width: 2.5, height: 2.5, bgcolor: '#9c27b0', borderRadius: '50%', animation: 'particle3 1.8s ease-in-out infinite 1s' }} />
      <Box sx={{ position: 'absolute', bottom: 8, right: 8, width: 2, height: 2, bgcolor: '#00bcd4', borderRadius: '50%', animation: 'particle4 2.2s ease-in-out infinite 0.8s' }} />
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
    if (stepIndex < currentStep) return 'completed';
    if (stepIndex === currentStep) return 'active';
    return 'pending';
  };

  const steps = [
    { 
      title: 'Initializing Analysis', 
      description: `Preparing work item data and analyzing ${relatedWorkItemsCount} related work items`,
      icon: 0
    },
    {
      title: 'Generating System Prompt',
      description: 'Creating intelligent system prompt for AI analysis',
      icon: 1
    },
    { 
      title: 'AI Model Activation', 
      description: `Connecting to advanced AI model - ${currentModel}`,
      icon: 2
    },
    {
      title: 'OpenArena Analysis',
      description: 'Running OpenArena analysis in the cloud',
      icon: 3
    },
    { 
      title: 'Intelligence Extraction', 
      description: 'Extracting insights and generating results',
      icon: 4
    }
  ];

  if (!isRunning) return null;

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
          {/* Header - More compact */}
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
              {/* Dynamic AI Icon with Smooth Transition */}
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
                Unleashing advanced AI analysis...
                {cycleIcons && (
                  <Box component="span" sx={{ ml: 1, fontSize: '0.8rem', opacity: 0.7 }}>
                    (Icon {currentIconType}/10)
                  </Box>
                )}
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
              <Chip 
                label={`Step ${currentStep + 1} of ${totalSteps}`}
                size="small"
                sx={{ 
                  bgcolor: 'rgba(255,255,255,0.2)', 
                  color: 'white', 
                  fontWeight: 'bold' 
                }}
              />
              {cycleIcons && (
                <Chip
                  label={`Icon ${currentIconType}/10`}
                  size="small"
                  sx={{ 
                    bgcolor: 'rgba(255,255,255,0.3)', 
                    color: 'white',
                    fontWeight: 'bold',
                    animation: 'pulse 2s ease-in-out infinite'
                  }}
                />
              )}
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
                {Math.round(progress)}%
              </Typography>
            </Box>
            <LinearProgress
              variant="determinate"
              value={progress}
              sx={{
                height: 8,
                borderRadius: 4,
                bgcolor: 'rgba(255,255,255,0.2)',
                '& .MuiLinearProgress-bar': {
                  borderRadius: 4,
                  background: 'linear-gradient(90deg, #06b6d4 0%, #3b82f6 50%, #8b5cf6 100%)',
                  transition: 'transform 0.3s ease-out'
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
                                 bgcolor: '#ff9800',
                                 width: 40,
                                 height: 40,
                                 animation: 'aiPulse 1.5s ease-in-out infinite'
                               }}>
                                 {step.icon === 2 ? (
                                   <AIIcon sx={{ fontSize: 24, animation: 'spin 2s linear infinite' }} />
                                 ) : step.icon === 4 ? (
                                   <LightbulbIcon sx={{ fontSize: 24, animation: 'flicker 1s ease-in-out infinite' }} />
                                 ) : step.icon === 0 ? (
                                   <SettingsIcon sx={{ fontSize: 24, animation: 'rotate 2s linear infinite' }} />
                                 ) : step.icon === 1 ? (
                                   <BuildIcon sx={{ fontSize: 24, animation: 'buildPulse 1.5s ease-in-out infinite' }} />
                                 ) : step.icon === 3 ? (
                                   <CloudQueueIcon sx={{ fontSize: 24, animation: 'float 2s ease-in-out infinite' }} />
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
          {realTimeMessage && (
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
                {realTimeMessage}
              </Typography>
            </Box>
          )}

          {/* Footer Info - Compact */}
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
              box-shadow: 0 0 0 0 rgba(255, 152, 0, 0.7);
            }
            50% { 
              transform: scale(1.1);
              box-shadow: 0 0 0 10px rgba(255, 152, 0, 0);
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
          @keyframes bounce {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-5px); }
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
          @keyframes robotWork {
            0%, 100% { 
              transform: translateY(0px) rotate(0deg);
            }
            25% { 
              transform: translateY(-2px) rotate(1deg);
            }
            50% { 
              transform: translateY(-4px) rotate(0deg);
            }
            75% { 
              transform: translateY(-2px) rotate(-1deg);
            }
          }
          @keyframes eyeBlink {
            0%, 90%, 100% { 
              height: 3px;
              opacity: 1;
            }
            95% { 
              height: 1px;
              opacity: 0.3;
            }
          }
          @keyframes antennaPulse {
            0%, 100% { 
              opacity: 1;
              transform: translateX(-50%) scale(1);
            }
            50% { 
              opacity: 0.6;
              transform: translateX(-50%) scale(1.2);
            }
          }
          @keyframes chestGlow {
            0%, 100% { 
              opacity: 0.3;
              box-shadow: 0 0 0 0 rgba(25, 118, 210, 0.3);
            }
            50% { 
              opacity: 0.8;
              box-shadow: 0 0 8px 4px rgba(25, 118, 210, 0.4);
            }
          }
          @keyframes armMove {
            0%, 100% { 
              transform: rotate(0deg);
            }
            25% { 
              transform: rotate(-10deg);
            }
            50% { 
              transform: rotate(0deg);
            }
            75% { 
              transform: rotate(10deg);
            }
          }
          @keyframes dataStream1 {
            0% { 
              opacity: 0;
              transform: translateX(0px) scale(0.5);
            }
            50% { 
              opacity: 1;
              transform: translateX(-15px) scale(1);
            }
            100% { 
              opacity: 0;
              transform: translateX(-30px) scale(0.5);
            }
          }
          @keyframes dataStream2 {
            0% { 
              opacity: 0;
              transform: translateX(0px) scale(0.5);
            }
            50% { 
              opacity: 1;
              transform: translateX(15px) scale(1);
            }
            100% { 
              opacity: 0;
              transform: translateX(30px) scale(0.5);
            }
          }
          @keyframes dataStream3 {
            0% { 
              opacity: 0;
              transform: translateX(0px) scale(0.5);
            }
            50% { 
              opacity: 1;
              transform: translateX(-10px) scale(1);
            }
            100% { 
              opacity: 0;
              transform: translateX(-20px) scale(0.5);
            }
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

export default AIProgressIndicator;
