import React from 'react';
import { Box } from '@mui/material';
import { SmartToy as DefaultModelIcon } from '@mui/icons-material';

// Helper function to get model display name from model ID
export const getModelDisplayName = (modelId) => {
  const modelNames = {
    'claude-4.1-opus': 'Claude 4.1 Opus',
    'gpt-5': 'GPT-5',
    'gemini-2.5-pro': 'Gemini 2.5 Pro',
    'llama-3-70b': 'Llama 3 70b',
    // Legacy model IDs for backward compatibility
    'claude-4-opus': 'Claude 4.1 Opus',
    'gemini-2-pro': 'Gemini 2.5 Pro'
  };
  return modelNames[modelId] || modelId || 'Not specified';
};

// Model icon component that uses PNG logos
export const ModelIcon = ({ modelId, sx, ...props }) => {
  const logoMap = {
    'claude-4.1-opus': '/icons/anthropic.png',
    'gpt-5': '/icons/openai.png',
    'gemini-2.5-pro': '/icons/google.png',
    'llama-3-70b': '/icons/meta.png',
    // Legacy model IDs for backward compatibility
    'claude-4-opus': '/icons/anthropic.png',
    'gemini-2-pro': '/icons/google.png'
  };

  const logoSrc = logoMap[modelId];
  
  if (logoSrc) {
    return (
      <Box
        component="img"
        src={logoSrc}
        alt={`${getModelDisplayName(modelId)} logo`}
        sx={{
          width: sx?.fontSize || 24,
          height: sx?.fontSize || 24,
          borderRadius: '4px',
          ...sx
        }}
        {...props}
      />
    );
  }

  // Fallback to default Material-UI icon
  return <DefaultModelIcon sx={sx} {...props} />;
};

export default ModelIcon;
