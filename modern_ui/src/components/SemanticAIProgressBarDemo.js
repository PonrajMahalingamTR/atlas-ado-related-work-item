import React, { useState } from 'react';
import {
  Box,
  Button,
  Paper,
  Typography,
  Container
} from '@mui/material';
import SemanticAIProgressBar from './SemanticAIProgressBar';

/**
 * Demo component to test the new SemanticAIProgressBar
 * This shows how the component would be used in the "AI Deep Dive" tab
 */
const SemanticAIProgressBarDemo = () => {
  const [isRunning, setIsRunning] = useState(false);

  const handleStart = () => {
    setIsRunning(true);
    
    // Auto-stop after 2 minutes (120 seconds) for demo
    setTimeout(() => {
      setIsRunning(false);
    }, 120000);
  };

  const handleStop = () => {
    setIsRunning(false);
  };

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Paper elevation={3} sx={{ p: 4 }}>
        <Typography variant="h4" gutterBottom>
          Semantic AI Progress Bar Demo
        </Typography>
        
        <Typography variant="body1" sx={{ mb: 3 }}>
          This demo shows the new SemanticAIProgressBar component that will be used 
          when users select the "AI Deep Dive" option (default tab). Click "Start Analysis" 
          to see the 2-minute progress animation with 5 phases:
        </Typography>

        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" sx={{ mb: 1 }}>Phase Overview:</Typography>
          <Typography variant="body2" component="ul" sx={{ pl: 2 }}>
            <li><strong>Phase 1:</strong> ADO Search & System Prompt Creation</li>
            <li><strong>Phase 2:</strong> LLM Analysis & Response Processing</li>
            <li><strong>Phase 3:</strong> Embedding Generation</li>
            <li><strong>Phase 4:</strong> Vector Database</li>
            <li><strong>Phase 5:</strong> Vector Similarity Search</li>
          </Typography>
        </Box>

        <Box sx={{ mb: 3, display: 'flex', gap: 2 }}>
          <Button 
            variant="contained" 
            color="primary" 
            onClick={handleStart}
            disabled={isRunning}
            sx={{
              background: 'linear-gradient(135deg, #1e3a8a 0%, #6366f1 50%, #8b5cf6 100%)',
              '&:hover': {
                background: 'linear-gradient(135deg, #1e40af 0%, #4f46e5 50%, #7c3aed 100%)',
              }
            }}
          >
            {isRunning ? 'Analysis Running...' : 'Start Semantic Analysis'}
          </Button>
          
          {isRunning && (
            <Button 
              variant="outlined" 
              color="secondary" 
              onClick={handleStop}
            >
              Stop Analysis
            </Button>
          )}
        </Box>

        {/* The new SemanticAIProgressBar component */}
        <SemanticAIProgressBar
          isRunning={isRunning}
          estimatedTime="2 minutes"
          currentModel="Claude 4.1 Opus"
          cycleIcons={true} // Enable icon cycling for demo
        />

        {isRunning && (
          <Box sx={{ mt: 2, p: 2, bgcolor: '#f5f5f5', borderRadius: 2 }}>
            <Typography variant="body2" color="text.secondary">
              <strong>Note:</strong> This is a UI demonstration. The progress bar will run for 2 minutes 
              showing different phases and real-time messages. In the actual implementation, 
              this will be integrated with the semantic similarity analysis business logic.
            </Typography>
          </Box>
        )}

        {!isRunning && (
          <Box sx={{ mt: 2, p: 2, bgcolor: '#e8f5e8', borderRadius: 2 }}>
            <Typography variant="body2" color="success.dark">
              Ready to start semantic analysis. This component is designed specifically 
              for the "AI Deep Dive" workflow and features custom messages and timing 
              different from the existing "AI Unleash Intelligence" progress bar.
            </Typography>
          </Box>
        )}
      </Paper>
    </Container>
  );
};

export default SemanticAIProgressBarDemo;
