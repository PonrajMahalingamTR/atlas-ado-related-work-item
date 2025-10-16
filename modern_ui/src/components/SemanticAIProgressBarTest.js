import React, { useState } from 'react';
import { Box, Button, Typography } from '@mui/material';
import SemanticAIProgressBar from './SemanticAIProgressBar';

/**
 * Simple test component to verify SemanticAIProgressBar works
 */
const SemanticAIProgressBarTest = () => {
  const [isRunning, setIsRunning] = useState(false);

  const handleStart = () => {
    setIsRunning(true);
    
    // Stop after 30 seconds for testing
    setTimeout(() => {
      setIsRunning(false);
    }, 30000);
  };

  const handleStop = () => {
    setIsRunning(false);
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Semantic AI Progress Bar Test
      </Typography>
      
      <Box sx={{ mb: 2 }}>
        <Button 
          variant="contained" 
          onClick={handleStart}
          disabled={isRunning}
          sx={{ mr: 2 }}
        >
          Start Test
        </Button>
        
        {isRunning && (
          <Button 
            variant="outlined" 
            onClick={handleStop}
          >
            Stop Test
          </Button>
        )}
      </Box>

      <SemanticAIProgressBar
        isRunning={isRunning}
        estimatedTime="2 minutes"
        currentModel="Claude 4.1 Opus"
        cycleIcons={true}
      />
    </Box>
  );
};

export default SemanticAIProgressBarTest;
